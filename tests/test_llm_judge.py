from __future__ import annotations

import json
from collections.abc import Iterator

from evalkit.core.case import TestCase
from evalkit.evaluators.llm_judge import (
    JudgeVerdict,
    LLMJudgeEvaluator,
    _extract_json,
    _format_rubric,
)
from evalkit.llm.base import LLMClient, LLMResponse, LLMUsage


class FakeClient(LLMClient):
    """Records calls and replays scripted responses."""

    provider = "fake"
    model = "fake-1"

    def __init__(self, responses: list[str]) -> None:
        self._responses: Iterator[str] = iter(responses)
        self.calls: list[tuple[str, str]] = []

    def complete_json(self, *, system: str, user: str, max_tokens: int = 1024, temperature: float = 0.0) -> LLMResponse:  # noqa: ARG002
        self.calls.append((system, user))
        text = next(self._responses)
        return LLMResponse(
            text=text,
            usage=LLMUsage(input_tokens=100, output_tokens=50, cost_usd=0.0001),
            model=self.model,
            provider=self.provider,
        )


def _verdict(score: int, reasoning: str = "ok") -> str:
    return json.dumps({
        "score": score,
        "reasoning": reasoning,
        "criteria_breakdown": [],
    })


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------
def test_extract_json_plain() -> None:
    out = _extract_json('{"score": 4, "reasoning": "x"}')
    assert out == {"score": 4, "reasoning": "x"}


def test_extract_json_with_code_fence() -> None:
    out = _extract_json('```json\n{"score": 5, "reasoning": "y"}\n```')
    assert out and out["score"] == 5


def test_extract_json_with_preamble() -> None:
    text = 'Sure! Here is my verdict:\n{"score": 3, "reasoning": "z"}\nThanks!'
    out = _extract_json(text)
    assert out and out["score"] == 3


def test_extract_json_returns_none_for_garbage() -> None:
    assert _extract_json("absolutely no json here") is None


# ---------------------------------------------------------------------------
# Rubric formatting
# ---------------------------------------------------------------------------
def test_rubric_string() -> None:
    assert _format_rubric("Be correct.") == "Be correct."


def test_rubric_list_of_strings() -> None:
    out = _format_rubric(["A", "B"])
    assert "1. A" in out and "2. B" in out


def test_rubric_list_of_dicts() -> None:
    out = _format_rubric([
        {"name": "accuracy", "description": "factually correct", "weight": 2},
        {"name": "fluency", "description": "well-written"},
    ])
    assert "**accuracy**" in out and "weight=2" in out
    assert "**fluency**" in out


def test_rubric_none() -> None:
    out = _format_rubric(None)
    assert "no further rubric" in out.lower()


# ---------------------------------------------------------------------------
# Single-pass evaluation
# ---------------------------------------------------------------------------
def test_single_pass_pass() -> None:
    client = FakeClient([_verdict(5, "looks great")])
    ev = LLMJudgeEvaluator(rubric="Be correct.", judge_model=client)
    case = TestCase(id="x", input="what is 2+2?", expected="4")
    r = ev.evaluate(case, "4")
    assert r.passed
    assert r.score == 1.0  # (5-1)/4
    assert r.metadata["raw_score_pass1"] == 5


def test_single_pass_fail() -> None:
    client = FakeClient([_verdict(2, "wrong")])
    ev = LLMJudgeEvaluator(rubric="Be correct.", judge_model=client)
    case = TestCase(id="x", input="2+2?", expected="4")
    r = ev.evaluate(case, "5")
    assert not r.passed
    assert r.score == 0.25  # (2-1)/4


def test_score_normalization_anchors() -> None:
    cases = [(1, 0.0), (2, 0.25), (3, 0.5), (4, 0.75), (5, 1.0)]
    for raw, expected in cases:
        c = FakeClient([_verdict(raw)])
        ev = LLMJudgeEvaluator(judge_model=c)
        r = ev.evaluate(TestCase(id="x", input="i"), "o")
        assert abs(r.score - expected) < 1e-9


# ---------------------------------------------------------------------------
# Two-pass averaging and disagreement
# ---------------------------------------------------------------------------
def test_two_pass_agreement() -> None:
    client = FakeClient([_verdict(4, "a"), _verdict(4, "b")])
    ev = LLMJudgeEvaluator(judge_model=client, two_pass=True)
    r = ev.evaluate(TestCase(id="x", input="i"), "o")
    assert r.passed
    assert r.metadata["disagreement"] == 0
    assert r.metadata["raw_score_pass2"] == 4


def test_two_pass_disagreement_flagged() -> None:
    client = FakeClient([_verdict(5, "great"), _verdict(2, "terrible")])
    ev = LLMJudgeEvaluator(
        judge_model=client, two_pass=True, disagreement_threshold=2.0
    )
    r = ev.evaluate(TestCase(id="x", input="i"), "o")
    assert r.metadata["disagreement"] == 3
    assert r.metadata["disagreement_flagged"] is True
    assert not r.passed  # disagreement >= threshold blocks pass
    assert "disagreement" in r.reasoning.lower()


def test_two_pass_below_disagreement_threshold_still_passes() -> None:
    client = FakeClient([_verdict(5), _verdict(4)])
    ev = LLMJudgeEvaluator(
        judge_model=client, two_pass=True, pass_threshold=4.0, disagreement_threshold=2.0
    )
    r = ev.evaluate(TestCase(id="x", input="i"), "o")
    assert r.passed
    assert r.metadata["mean_raw_score"] == 4.5


# ---------------------------------------------------------------------------
# Robustness: malformed response, retry, validation error
# ---------------------------------------------------------------------------
def test_malformed_response_retried() -> None:
    client = FakeClient(["sorry, I can't comply", _verdict(3)])
    ev = LLMJudgeEvaluator(judge_model=client)
    r = ev.evaluate(TestCase(id="x", input="i"), "o")
    assert r.metadata["raw_score_pass1"] == 3
    # both calls landed on the FakeClient
    assert len(client.calls) == 2
    # second call has the reminder
    assert "JSON only" in client.calls[1][1] or "strict JSON" in client.calls[1][1]


def test_double_malformed_response_returns_error_result() -> None:
    client = FakeClient(["nope", "still nope"])
    ev = LLMJudgeEvaluator(judge_model=client)
    r = ev.evaluate(TestCase(id="x", input="i"), "o")
    assert not r.passed
    assert r.metadata.get("error") == "parse_failure"


def test_validation_error_invalid_score() -> None:
    bad = json.dumps({"score": 9, "reasoning": "out of range"})
    client = FakeClient([bad, bad])  # second extracts but still invalid
    ev = LLMJudgeEvaluator(judge_model=client)
    r = ev.evaluate(TestCase(id="x", input="i"), "o")
    # Schema validation should kick in (invalid) and surface as parse error
    assert not r.passed


def test_empty_output_short_circuits() -> None:
    client = FakeClient([])  # would error if called
    ev = LLMJudgeEvaluator(judge_model=client)
    r = ev.evaluate(TestCase(id="x", input="i"), "")
    assert not r.passed
    assert r.metadata["empty_output"] is True
    assert client.calls == []


# ---------------------------------------------------------------------------
# Cost tracking
# ---------------------------------------------------------------------------
def test_cost_tracked_per_pass() -> None:
    client = FakeClient([_verdict(4)])
    ev = LLMJudgeEvaluator(judge_model=client)
    r = ev.evaluate(TestCase(id="x", input="i"), "o")
    u = r.metadata["usage_pass1"]
    assert u["input_tokens"] == 100
    assert u["output_tokens"] == 50
    assert u["cost_usd"] > 0
    assert u["provider"] == "fake"


def test_cost_tracked_two_pass() -> None:
    client = FakeClient([_verdict(4), _verdict(4)])
    ev = LLMJudgeEvaluator(judge_model=client, two_pass=True)
    r = ev.evaluate(TestCase(id="x", input="i"), "o")
    assert "usage_pass1" in r.metadata
    assert "usage_pass2" in r.metadata


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------
def test_prompt_includes_input_expected_actual_and_rubric() -> None:
    client = FakeClient([_verdict(4)])
    ev = LLMJudgeEvaluator(rubric="Be concise and correct.", judge_model=client)
    case = TestCase(id="x", input="What is the capital of France?", expected="Paris")
    sys_msg, user_msg = ev.build_prompt(case, "Paris is the capital.")
    assert "calibrated" in sys_msg.lower()
    assert "1 — Unacceptable" in sys_msg or "1 — Unacceptable" in sys_msg
    assert "Be concise and correct." in user_msg
    assert "What is the capital of France?" in user_msg
    assert "Paris" in user_msg
    assert "Paris is the capital." in user_msg


def test_per_case_rubric_overrides_default() -> None:
    client = FakeClient([_verdict(4)])
    ev = LLMJudgeEvaluator(rubric="default rubric", judge_model=client)
    case = TestCase(
        id="x", input="i", metadata={"rubric": "case-specific rubric"}
    )
    _, user_msg = ev.build_prompt(case, "o")
    assert "case-specific rubric" in user_msg
    assert "default rubric" not in user_msg


# ---------------------------------------------------------------------------
# Verdict schema sanity
# ---------------------------------------------------------------------------
def test_verdict_rejects_out_of_range_score() -> None:
    import pytest
    from pydantic import ValidationError as VE
    with pytest.raises(VE):
        JudgeVerdict.model_validate({"score": 6, "reasoning": "x"})
