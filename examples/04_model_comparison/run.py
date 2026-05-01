"""04_model_comparison — same dataset, two targets, comparison report.

Demonstrates the framework's killer feature: side-by-side comparison.
Runs the same 15-question QA dataset against Claude Sonnet and GPT-4o-mini,
then produces a markdown comparison report showing per-evaluator deltas
and any cases where the models disagree.

If neither API key is set, the script uses two distinct mock LLMs that
disagree on a few questions, so the comparison report still has signal.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from evalkit import CallableTarget, Runner, load_dataset
from evalkit.core.compare import compare_runs, format_comparison_markdown
from evalkit.core.target import Target
from evalkit.evaluators import ExactMatchEvaluator
from evalkit.llm import build_client
from evalkit.reports import render_dashboard, render_markdown


def _llm_callable(spec: str):  # type: ignore[no-untyped-def]
    """Wrap an LLMClient as a callable target. The client is built once
    per Runner so token bookkeeping survives across cases."""
    client = build_client(spec)

    def _fn(input_value):  # type: ignore[no-untyped-def]
        resp = client.complete_json(
            system="Answer the question. Be terse: provide the requested form only, "
                   "no explanation. Always give your best answer in the format requested.",
            user=input_value["prompt"],
            max_tokens=80,
            temperature=0.0,
        )
        return resp.text.strip()
    return _fn


# ---------------------------------------------------------------------------
# Mock LLMs (used when no API key is available)
# ---------------------------------------------------------------------------
_TRUTH = {
    "qa_001": "Paris", "qa_002": "Au", "qa_003": "Jane Austen",
    "qa_004": "391", "qa_005": "101", "qa_006": "1945",
    "qa_007": "100", "qa_008": "Jupiter", "qa_009": "Leonardo da Vinci",
    "qa_010": "12", "qa_011": "H2O", "qa_012": "Neil Armstrong",
    "qa_013": "7", "qa_014": "George Orwell", "qa_015": "3.0e8",
}
_MOCK_A_WRONG = {"qa_004": "397", "qa_015": "3e8 m/s with units"}
_MOCK_B_WRONG = {"qa_005": "103", "qa_011": "water (H2O)", "qa_009": "Da Vinci"}


def _lookup_factory(wrong_overrides: dict[str, str]):  # type: ignore[no-untyped-def]
    """Build a mock that maps prompts back to their case ids using a
    simple substring match against the prompts in the dataset."""
    def fn(input_value):  # type: ignore[no-untyped-def]
        prompt = input_value["prompt"].lower()
        # cheap fingerprint: pick a unique 3-word slice
        markers = {
            "qa_001": "capital of france",
            "qa_002": "chemical symbol for gold",
            "qa_003": "pride and prejudice",
            "qa_004": "17 multiplied by 23",
            "qa_005": "smallest prime number",
            "qa_006": "world war ii end",
            "qa_007": "boiling point of water",
            "qa_008": "largest planet",
            "qa_009": "painted the mona lisa",
            "qa_010": "square root of 144",
            "qa_011": "formula for water",
            "qa_012": "first man on the moon",
            "qa_013": "how many continents",
            "qa_014": "author of '1984'",
            "qa_015": "speed of light",
        }
        for case_id, marker in markers.items():
            if marker in prompt:
                return wrong_overrides.get(case_id, _TRUTH[case_id])
        return "I don't know"
    return fn


def _build_targets() -> tuple[Target, Target, str]:
    """Returns (target_a, target_b, mode) — 'live' or 'mock'."""
    if os.environ.get("ANTHROPIC_API_KEY") and os.environ.get("OPENAI_API_KEY"):
        a = CallableTarget(_llm_callable("anthropic:claude-sonnet-4-6"), name="claude-sonnet-4-6")
        b = CallableTarget(_llm_callable("openai:gpt-4o-mini"), name="gpt-4o-mini")
        return a, b, "live"
    a = CallableTarget(_lookup_factory(_MOCK_A_WRONG), name="mock-a")
    b = CallableTarget(_lookup_factory(_MOCK_B_WRONG), name="mock-b")
    return a, b, "mock"


async def main() -> None:
    here = Path(__file__).parent
    dataset = load_dataset(here / "dataset.jsonl")

    target_a, target_b, mode = _build_targets()
    print(f"target mode: {mode}", file=sys.stderr)

    runs_root = here / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)

    # We deliberately use a forgiving exact_match (case + punctuation insensitive)
    # so superficial formatting differences don't blow up the comparison.
    evaluators = [ExactMatchEvaluator(ignore_case=True, ignore_punctuation=True)]

    print(f"\n=== running {target_a.summary().get('name')} ===", file=sys.stderr)
    rep_a = await Runner(target=target_a, evaluators=evaluators, runs_root=runs_root).run(dataset)
    render_markdown(rep_a, runs_root / rep_a.run_id / "report.md")
    render_dashboard(rep_a, runs_root / rep_a.run_id / "dashboard.html")

    print(f"\n=== running {target_b.summary().get('name')} ===", file=sys.stderr)
    rep_b = await Runner(target=target_b, evaluators=evaluators, runs_root=runs_root).run(dataset)
    render_markdown(rep_b, runs_root / rep_b.run_id / "report.md")
    render_dashboard(
        rep_b, runs_root / rep_b.run_id / "dashboard.html", previous=rep_a
    )

    diff = compare_runs(rep_a, rep_b)
    comparison_md = format_comparison_markdown(diff)
    comparison_path = runs_root / "comparison.md"
    comparison_path.write_text(comparison_md, encoding="utf-8")

    # Print summary
    print()
    print(f"target_a ({target_a.summary().get('name')}): pass {rep_a.pass_rate*100:.1f}%")
    print(f"target_b ({target_b.summary().get('name')}): pass {rep_b.pass_rate*100:.1f}%")
    print(f"\ndelta pass-rate: {diff.delta_pass_rate*100:+.1f}pp "
          f"({len(diff.flips)} cases flipped)")
    if diff.flips:
        for f in diff.flips:
            arrow = "improved" if f.direction == "improved" else "regressed"
            print(f"  {f.case_id} {arrow}: {f.a_passed} -> {f.b_passed}")
    print(f"\nrun_a:      {runs_root / rep_a.run_id}")
    print(f"run_b:      {runs_root / rep_b.run_id}")
    print(f"comparison: {comparison_path}")


if __name__ == "__main__":
    asyncio.run(main())
