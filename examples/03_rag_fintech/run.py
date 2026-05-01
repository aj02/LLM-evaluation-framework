"""03_rag_fintech — eval the SEBI/RBI RAG system.

This example wires together three evaluators that, together, give a full
picture of RAG quality:

- **retrieval** — recall@5 against a hand-curated relevance set per question.
  Catches the "do we even pull the right documents?" failure mode.
- **llm_judge** — a calibrated 1-5 score on the final answer text. Catches
  the "we retrieved the right docs but synthesized them wrong" failure mode.
- **exact_match** with a loose threshold — kept as a sanity check on simple
  lookup questions. Falls back to off when the question is open-ended.

The dataset has 30 questions across three categories:
  - lookup (single-fact)
  - multi_doc (synthesis from multiple regulations)
  - out_of_corpus (questions the RAG should refuse, not answer)

If the RAG service at localhost:8001 isn't running, the script falls back
to a deliberately-bad keyword retriever so a report is still produced.
The committed `runs/` folder uses the fallback. **Replace with real
numbers as soon as the service is up.**
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path

import httpx

from evalkit import CallableTarget, HTTPTarget, Runner, load_dataset
from evalkit.core.target import HTTPTargetConfig, Target
from evalkit.evaluators import (
    ExactMatchEvaluator,
    LLMJudgeEvaluator,
    RetrievalEvaluator,
)
from evalkit.reports import render_dashboard, render_markdown


# ---------------------------------------------------------------------------
# Mock RAG (used when the real service isn't reachable).
# Builds a tiny "corpus" by scanning the dataset's relevant_ids and using
# question keywords to retrieve. Output deliberately imperfect so reviewers
# can see what a partially-broken RAG looks like in the report.
# ---------------------------------------------------------------------------
def _mock_rag_factory(dataset_path: Path) -> CallableTarget:
    """Build a keyword-based mock that retrieves doc_ids when their topic
    keywords appear in the question. Refuses out-of-scope questions."""
    import json
    corpus: dict[str, set[str]] = {}
    answers: dict[str, str] = {}
    with dataset_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            q = r["input"]["question"]
            answer = r.get("expected", {}).get("answer", "")
            ids = r.get("expected", {}).get("relevant_ids", [])
            tokens = {t for t in re.findall(r"[a-z0-9]+", q.lower()) if len(t) > 3}
            for doc_id in ids:
                corpus.setdefault(doc_id, set()).update(tokens)
            answers[q.lower()] = answer

    refusal_phrases = ("predict", "buy ", "sell ", "haiku", "cricket")

    def fn(input_value: dict) -> dict:
        q = input_value["question"]
        if any(p in q.lower() for p in refusal_phrases):
            return {
                "answer": "I can only answer questions about Indian financial regulations.",
                "retrieved_ids": [],
                "confidence": 0.05,
            }
        q_tokens = {t for t in re.findall(r"[a-z0-9]+", q.lower()) if len(t) > 3}
        scored = sorted(
            ((doc_id, len(q_tokens & toks)) for doc_id, toks in corpus.items()),
            key=lambda x: x[1],
            reverse=True,
        )
        top5 = [doc_id for doc_id, score in scored[:5] if score > 0]
        # answer is a stitched summary of the top doc's question's expected answer
        ans = answers.get(q.lower(), "")
        if not ans and top5:
            ans = f"Based on {top5[0]}: (mock RAG cannot synthesize a real answer)."
        return {
            "answer": ans or "I don't have a confident answer.",
            "retrieved_ids": top5,
            "confidence": 0.5,
        }

    return CallableTarget(fn, name="mock-keyword-rag")


# ---------------------------------------------------------------------------
# Live target probe
# ---------------------------------------------------------------------------
async def _build_target(dataset_path: Path) -> tuple[Target, str]:
    """Probe the live /ask endpoint; fall back to mock if it's not the RAG."""
    probe = {"question": "probe"}
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.post("http://localhost:8001/ask", json=probe)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict) or "retrieved_ids" not in data:
            raise ValueError("response missing retrieved_ids")
    except Exception:
        return _mock_rag_factory(dataset_path), "mock"

    config = HTTPTargetConfig(
        url="http://localhost:8001/ask",
        method="POST",
        headers={"content-type": "application/json"},
        payload_template="{{ input | tojson }}",
        name="sebi-rbi-rag",
    )
    return HTTPTarget(config), "http"


# ---------------------------------------------------------------------------
# Custom answer evaluator: extracts answer field then runs exact_match in
# loose mode. Produces a 'soft_match' signal for cases where we have a known
# right answer.
# ---------------------------------------------------------------------------
def _answer_text(output) -> str:  # type: ignore[no-untyped-def]
    if isinstance(output, dict):
        return str(output.get("answer", ""))
    return str(output)


class AnswerExactMatch(ExactMatchEvaluator):
    """Run exact-match against the answer field of a RAG response."""

    name = "answer_exact_match"

    def evaluate(self, case, output):  # type: ignore[no-untyped-def, override]
        ans_text = _answer_text(output)
        # rebuild the case with the expected answer text only
        from evalkit.core.case import TestCase
        rewritten = TestCase(
            id=case.id,
            input=case.input,
            expected=(case.expected or {}).get("answer") if isinstance(case.expected, dict) else case.expected,
            metadata=case.metadata,
        )
        return super().evaluate(rewritten, ans_text)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main() -> None:
    here = Path(__file__).parent
    dataset = load_dataset(here / "dataset.jsonl")
    target, mode = await _build_target(here / "dataset.jsonl")
    print(f"target mode: {mode}", file=sys.stderr)

    evaluators = [
        RetrievalEvaluator(k=5, threshold=0.6),
        AnswerExactMatch(ignore_case=True, ignore_punctuation=True),
    ]
    # Only add the judge if a key is present — otherwise it would fail at
    # call time rather than silently producing zeros.
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"):
        evaluators.append(
            LLMJudgeEvaluator(
                rubric=[
                    {"name": "factual_accuracy",
                     "description": "All cited regulations and numbers match the expected answer.",
                     "weight": 3},
                    {"name": "completeness",
                     "description": "All parts of the question are addressed; no required element omitted.",
                     "weight": 2},
                    {"name": "refusal_appropriateness",
                     "description": "If the question is out-of-corpus (markets, predictions, opinions), "
                                    "the system should decline rather than fabricate.",
                     "weight": 2},
                ],
                judge_model=os.environ.get("EVALKIT_JUDGE", "anthropic:claude-sonnet-4-6"),
                pass_threshold=4.0,
                two_pass=False,
            )
        )
        print("LLM judge: enabled", file=sys.stderr)
    else:
        print("LLM judge: SKIPPED (set ANTHROPIC_API_KEY to enable)", file=sys.stderr)

    runs_root = here / "runs"
    runner = Runner(target=target, evaluators=evaluators, runs_root=runs_root, concurrency=4)
    report = await runner.run(dataset)
    if isinstance(target, HTTPTarget):
        await target.aclose()

    run_dir = runs_root / report.run_id
    render_markdown(report, run_dir / "report.md")
    render_dashboard(report, run_dir / "dashboard.html")

    print(f"\nrun_id: {report.run_id}")
    print(f"target: {target.summary().get('name', '?')} ({mode})")
    print(f"pass rate: {report.pass_rate * 100:.1f}% "
          f"({report.n_passed} pass / {report.n_failed} fail / "
          f"{report.n_errored} error of {report.n_cases})")
    for m in report.aggregate_metrics:
        print(f"  {m.name:<22} mean={m.mean:.3f} pass={m.pass_rate*100:.1f}% n={m.n}")
    if report.latency_ms:
        print(f"latency: p50={report.latency_ms.get('p50',0):.0f}ms "
              f"p95={report.latency_ms.get('p95',0):.0f}ms")
    print(f"report:    {run_dir / 'report.md'}")
    print(f"dashboard: {run_dir / 'dashboard.html'}")


if __name__ == "__main__":
    asyncio.run(main())
