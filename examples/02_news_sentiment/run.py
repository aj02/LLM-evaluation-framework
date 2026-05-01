"""02_news_sentiment — eval against a sentiment classifier.

This example assumes a sentiment analyzer is running at
``http://localhost:8000/analyze``. If you have it running, run with::

    python examples/02_news_sentiment/run.py

If you don't, the script falls back to a simple keyword-based mock so you
still see what a full evalkit run looks like end-to-end. The mock is NOT
the framework — it's just here so this example produces real artifacts on
every checkout.

The dataset is 20 financial headlines labelled positive/negative/neutral.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx

from evalkit import CallableTarget, HTTPTarget, Runner, load_dataset
from evalkit.core.target import HTTPTargetConfig, Target
from evalkit.evaluators import ExactMatchEvaluator
from evalkit.reports import render_dashboard, render_markdown

POSITIVE = ("beat", "record", "raised", "strong", "wins", "secured", "rally",
            "expand", "growth", "growing", "clean", "zero observation",
            "completes", "merger")
NEGATIVE = ("miss", "missed", "fall", "fell", "delays", "delayed", "stress",
            "slump", "circuit", "hike", "weakens", "rise", "rose", "resign",
            "headwinds", "concern", "scandal", "irregular", "loss", "down",
            "narrow")


def _mock_sentiment(input_value: dict) -> str:
    """Cheap keyword-based mock so this example runs end-to-end without the
    real service. Not a model — it's a stand-in so the report renders."""
    text = (input_value.get("headline", "") + " " + input_value.get("body", "")).lower()
    pos = sum(text.count(w) for w in POSITIVE)
    neg = sum(text.count(w) for w in NEGATIVE)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


async def _build_target() -> tuple[Target, str]:
    """Try the live /analyze endpoint with a real probe; fall back to mock
    if the response isn't a valid sentiment dict. A naive /health check
    isn't enough — anything could be on localhost:8000."""
    probe = {"headline": "probe", "body": "probe"}
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.post("http://localhost:8000/analyze", json=probe)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict) or "sentiment" not in data:
            raise ValueError("response missing 'sentiment' key")
    except Exception:
        return CallableTarget(_mock_sentiment, name="mock-keyword-sentiment"), "mock"

    config = HTTPTargetConfig(
        url="http://localhost:8000/analyze",
        method="POST",
        headers={"content-type": "application/json"},
        payload_template="{{ input | tojson }}",
        response_path="sentiment",
        name="news-sentiment-analyzer",
    )
    return HTTPTarget(config), "http"


async def main() -> None:
    here = Path(__file__).parent
    dataset = load_dataset(here / "dataset.jsonl")
    target, mode = await _build_target()
    print(f"target mode: {mode}", file=sys.stderr)

    runs_root = here / "runs"
    runner = Runner(
        target=target,
        evaluators=[ExactMatchEvaluator(ignore_case=True, ignore_punctuation=True)],
        runs_root=runs_root,
    )
    report = await runner.run(dataset)
    if isinstance(target, HTTPTarget):
        await target.aclose()

    run_dir = runs_root / report.run_id
    render_markdown(report, run_dir / "report.md")
    render_dashboard(report, run_dir / "dashboard.html")

    print(f"\nrun_id: {report.run_id}")
    print(f"pass rate: {report.pass_rate * 100:.1f}% "
          f"({report.n_passed} pass / {report.n_failed} fail / "
          f"{report.n_errored} error of {report.n_cases})")
    for m in report.aggregate_metrics:
        print(f"  {m.name}: mean={m.mean:.3f} pass={m.pass_rate*100:.1f}% n={m.n}")
    if report.latency_ms:
        p50 = report.latency_ms.get("p50", 0)
        p95 = report.latency_ms.get("p95", 0)
        print(f"latency: p50={p50:.0f}ms p95={p95:.0f}ms")
    print(f"report:    {run_dir / 'report.md'}")
    print(f"dashboard: {run_dir / 'dashboard.html'}")


if __name__ == "__main__":
    asyncio.run(main())
