"""01_quickstart — minimal in-Python eval against a CallableTarget.

The "system under test" is `uppercase_target`. This script is a complete
hello-world for evalkit: load a dataset, run it, print the report.

Run from the repo root:

    python examples/01_quickstart/run.py
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from evalkit import CallableTarget, Runner, load_dataset
from evalkit.evaluators import ExactMatchEvaluator
from evalkit.reports import render_dashboard, render_markdown


def uppercase_target(input_value: dict) -> str:
    """Trivial system under test: returns the upper-cased input text."""
    return input_value["text"].upper()


async def main() -> None:
    here = Path(__file__).parent
    dataset = load_dataset(here / "dataset.jsonl")
    target = CallableTarget(uppercase_target, name="uppercase")
    runs_root = here / "runs"
    runner = Runner(target=target, evaluators=[ExactMatchEvaluator()], runs_root=runs_root)
    report = await runner.run(dataset)

    run_dir = runs_root / report.run_id
    render_markdown(report, run_dir / "report.md")
    render_dashboard(report, run_dir / "dashboard.html")

    print(f"\nrun_id: {report.run_id}")
    print(f"pass rate: {report.pass_rate * 100:.1f}% "
          f"({report.n_passed}/{report.n_cases})")
    for m in report.aggregate_metrics:
        print(f"  {m.name}: mean={m.mean:.3f} pass={m.pass_rate*100:.1f}% n={m.n}")
    print(f"report:    {run_dir / 'report.md'}")
    print(f"dashboard: {run_dir / 'dashboard.html'}")


if __name__ == "__main__":
    asyncio.run(main())
