"""LLM-as-judge evaluator.

Design notes
============

This is the most consequential evaluator: when expected outputs are loose
(open-ended QA, summaries, rationales), exact match and embeddings can't
tell you whether an answer is *good*. The judge can — but only if its
prompt is calibrated, its output is structured, and its agreement with
itself is measured.

Five things matter, in priority order:

1. **Calibration anchors.** The judge prompt explicitly defines what each
   score (1–5) means. Without anchors, judges drift toward the middle of
   the scale and stop discriminating.
2. **Structured output.** The judge returns strict JSON validated against a
   Pydantic schema. We do NOT trust the judge to also self-grade; the
   `passed` boolean is computed from `score >= pass_threshold`, not
   self-reported.
3. **Two-pass agreement.** Optional second pass with the same prompt. We
   report the mean score and flag disagreement when scores differ by more
   than ``disagreement_threshold`` (default 1.0 on the 1–5 scale). This is
   a cheap noise-detector — if it fires often, the rubric is ambiguous or
   the system is on a hard boundary.
4. **Cost is visible.** Every call's tokens and dollar cost are recorded
   in the EvaluatorResult metadata so a run summary can sum them.
5. **Failure is informative, not silent.** Malformed JSON is retried once
   with an explicit reminder. If retry fails, the evaluator returns
   ``passed=False`` with an error reasoning instead of exploding the run.
"""
from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from evalkit.core.case import TestCase
from evalkit.core.result import EvaluatorResult
from evalkit.llm import LLMClient, build_client


# ---------------------------------------------------------------------------
# Judge output schema (what the LLM must produce)
# ---------------------------------------------------------------------------
class CriterionScore(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    score: int = Field(..., ge=1, le=5)
    reasoning: str = ""


class JudgeVerdict(BaseModel):
    """Schema the judge model must return as JSON."""

    model_config = ConfigDict(extra="ignore")

    score: int = Field(..., ge=1, le=5, description="Overall 1-5 holistic score.")
    reasoning: str = Field(..., description="One paragraph explaining the score.")
    criteria_breakdown: list[CriterionScore] = Field(
        default_factory=list,
        description="Per-criterion 1-5 scores. Optional if rubric is a single string.",
    )


# ---------------------------------------------------------------------------
# Prompt template — the craft of this framework
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """\
You are a careful, calibrated evaluator. Your job is to score whether an AI \
system's actual output meets the requirements of a test case, using the \
provided rubric. You must be specific, neutral, and honest — including when \
the output is wrong, partially wrong, or fluently misleading.

Return STRICT JSON matching this schema (no prose before or after the JSON, \
no markdown code fences):

{
  "score": <integer 1-5>,
  "reasoning": "<one short paragraph; cite specific phrases from the actual \
output>",
  "criteria_breakdown": [
    {"name": "<criterion>", "score": <1-5>, "reasoning": "<one sentence>"},
    ...
  ]
}

Score calibration (use the WHOLE scale; do not default to 3):
  5 — Excellent. Fully correct, complete, and well-supported. A subject-matter \
expert would accept this answer without revision.
  4 — Good. Correct in substance with minor issues (small omissions, awkward \
phrasing, an unimportant inaccuracy) that a reader would tolerate.
  3 — Mixed. Partially correct — captures the right idea but has a material \
flaw: a missing required element, a misleading framing, or a single \
factual error that changes the meaning.
  2 — Poor. Mostly wrong or misleading. Some surface relevance but the \
substantive answer is incorrect, hallucinated, or off-topic.
  1 — Unacceptable. Completely wrong, fabricated, refuses an answerable \
question, or is unrelated to the input.

Rules:
- The score is integer-valued. No 4.5s.
- Cite specific text from the actual output in your reasoning. Vague \
reasoning is itself a quality issue and you should reduce your own confidence.
- If the expected output is provided, treat it as the gold reference: an \
answer that contradicts it on substance is at most a 2 unless the expected \
itself is wrong, in which case explain that.
- If the expected output is missing, score against the rubric and the \
input's stated requirements.
- Do NOT reward verbose hedging. A confidently wrong answer and a hedged \
wrong answer score the same.
- Output JSON only. Any text outside the JSON object is a protocol violation.
"""

_USER_PROMPT_TEMPLATE = """\
# Rubric
{rubric_block}

# Test case input
{input_block}

# Expected output
{expected_block}

# Actual output (from the system under test)
{actual_block}

Respond with the JSON verdict only."""


def _format_block(value: Any, *, max_chars: int = 8000) -> str:
    """Render a value as a fenced block, truncating very long inputs."""
    if value is None:
        return "(none provided)"
    if isinstance(value, str):
        s = value
    else:
        try:
            s = json.dumps(value, indent=2, ensure_ascii=False)
        except (TypeError, ValueError):
            s = str(value)
    if len(s) > max_chars:
        s = s[: max_chars - 50] + f"\n... [truncated, {len(s) - max_chars + 50} chars omitted]"
    return s


def _format_rubric(rubric: str | list[str] | list[dict[str, Any]] | None) -> str:
    if rubric is None:
        return ("Score the actual output for correctness and completeness against "
                "the input requirements. There is no further rubric.")
    if isinstance(rubric, str):
        return rubric.strip()
    # list — could be strings or dicts with name + description
    lines: list[str] = []
    for i, item in enumerate(rubric, start=1):
        if isinstance(item, str):
            lines.append(f"{i}. {item}")
        elif isinstance(item, dict):
            name = item.get("name", f"criterion_{i}")
            desc = item.get("description") or item.get("desc") or ""
            weight = item.get("weight")
            suffix = f" (weight={weight})" if weight is not None else ""
            lines.append(f"{i}. **{name}**{suffix}: {desc}".rstrip(": ").rstrip())
        else:
            lines.append(f"{i}. {item}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON extraction — small recovery layer
# ---------------------------------------------------------------------------
_JSON_OBJ_RE = re.compile(r"\{(?:[^{}]|(?:\{[^{}]*\}))*\}", re.DOTALL)


def _extract_json(text: str) -> dict[str, Any] | None:
    """Find the first JSON object in ``text`` and return it, or None."""
    text = text.strip()
    # Strip code-fence preambles if the model ignored instructions.
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = _JSON_OBJ_RE.search(text)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------
class LLMJudgeEvaluator:
    """LLM-as-judge with structured rubric scoring."""

    name = "llm_judge"

    def __init__(
        self,
        *,
        rubric: str | list[Any] | None = None,
        judge_model: str | LLMClient = "anthropic:claude-sonnet-4-6",
        pass_threshold: float = 4.0,
        two_pass: bool = False,
        disagreement_threshold: float = 1.0,
        max_tokens: int = 700,
        temperature: float = 0.0,
    ) -> None:
        self.rubric = rubric
        self.pass_threshold = pass_threshold
        self.two_pass = two_pass
        self.disagreement_threshold = disagreement_threshold
        self.max_tokens = max_tokens
        self.temperature = temperature

        if isinstance(judge_model, str):
            self._client_spec = judge_model
            self._client: LLMClient | None = None  # built lazily
        else:
            self._client_spec = f"{judge_model.provider}:{judge_model.model}"
            self._client = judge_model

    def _client_lazy(self) -> LLMClient:
        if self._client is None:
            self._client = build_client(self._client_spec)
        return self._client

    # -----------------------------------------------------------------------
    # Prompt construction (exposed so it can be inspected/tested)
    # -----------------------------------------------------------------------
    def build_prompt(self, case: TestCase, output: Any) -> tuple[str, str]:
        """Returns ``(system, user)`` — the messages sent to the judge."""
        case_rubric = case.metadata.get("rubric", self.rubric)
        user = _USER_PROMPT_TEMPLATE.format(
            rubric_block=_format_rubric(case_rubric),
            input_block=_format_block(case.input),
            expected_block=_format_block(case.expected),
            actual_block=_format_block(output),
        )
        return _SYSTEM_PROMPT, user

    # -----------------------------------------------------------------------
    # Single judge call
    # -----------------------------------------------------------------------
    def _judge_once(
        self, case: TestCase, output: Any
    ) -> tuple[JudgeVerdict | None, dict[str, Any], str]:
        system, user = self.build_prompt(case, output)
        client = self._client_lazy()

        resp = client.complete_json(
            system=system,
            user=user,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        usage = {
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
            "cost_usd": resp.usage.cost_usd,
            "model": resp.model,
            "provider": resp.provider,
        }

        data = _extract_json(resp.text)
        if data is None:
            # Retry once with an explicit nudge.
            retry = client.complete_json(
                system=system,
                user=user + "\n\nReminder: respond with strict JSON only, no prose.",
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            usage["input_tokens"] += retry.usage.input_tokens
            usage["output_tokens"] += retry.usage.output_tokens
            usage["cost_usd"] += retry.usage.cost_usd
            data = _extract_json(retry.text)
            if data is None:
                return None, usage, resp.text

        try:
            verdict = JudgeVerdict.model_validate(data)
        except ValidationError as e:
            return None, usage, f"validation_error: {e}"
        return verdict, usage, ""

    # -----------------------------------------------------------------------
    # Public evaluate
    # -----------------------------------------------------------------------
    def evaluate(self, case: TestCase, output: Any) -> EvaluatorResult:
        if output is None or (isinstance(output, str) and not output.strip()):
            return EvaluatorResult(
                name=self.name,
                score=0.0,
                passed=False,
                reasoning="empty output; nothing to judge",
                metadata={"empty_output": True},
            )

        # Pass 1
        v1, u1, err1 = self._judge_once(case, output)
        if v1 is None:
            return EvaluatorResult(
                name=self.name,
                score=0.0,
                passed=False,
                reasoning=f"judge_parse_error: {err1[:300]}",
                metadata={"error": "parse_failure", "usage_pass1": u1},
            )

        # Optionally a second pass
        v2: JudgeVerdict | None = None
        u2: dict[str, Any] | None = None
        if self.two_pass:
            v2, u2, _ = self._judge_once(case, output)

        if v2 is None:
            mean_raw = float(v1.score)
            disagreement = 0.0
        else:
            mean_raw = (v1.score + v2.score) / 2.0
            disagreement = abs(v1.score - v2.score)

        # Map 1..5 → 0..1.
        norm = max(0.0, min(1.0, (mean_raw - 1.0) / 4.0))
        passed = mean_raw >= self.pass_threshold and disagreement < self.disagreement_threshold

        meta: dict[str, Any] = {
            "raw_score_pass1": v1.score,
            "criteria_pass1": [c.model_dump() for c in v1.criteria_breakdown],
            "usage_pass1": u1,
            "pass_threshold": self.pass_threshold,
            "disagreement_threshold": self.disagreement_threshold,
            "mean_raw_score": mean_raw,
            "two_pass": self.two_pass,
        }
        if v2 is not None:
            meta["raw_score_pass2"] = v2.score
            meta["criteria_pass2"] = [c.model_dump() for c in v2.criteria_breakdown]
            meta["usage_pass2"] = u2
            meta["disagreement"] = disagreement
            meta["disagreement_flagged"] = disagreement >= self.disagreement_threshold

        reasoning = v1.reasoning
        if v2 is not None and disagreement >= self.disagreement_threshold:
            reasoning = (
                f"[two-pass disagreement {disagreement:.0f}] pass1 ({v1.score}/5): "
                f"{v1.reasoning} || pass2 ({v2.score}/5): {v2.reasoning}"
            )

        return EvaluatorResult(
            name=self.name,
            score=norm,
            passed=passed,
            reasoning=reasoning,
            metadata=meta,
        )
