"""Runner: orchestrates running cases against a target with evaluators."""
from __future__ import annotations

import asyncio
import statistics
import time
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
)

from evalkit import __version__
from evalkit.core.case import TestCase
from evalkit.core.dataset import Dataset
from evalkit.core.result import (
    AggregateMetric,
    CaseResult,
    EvaluatorResult,
    RunReport,
)
from evalkit.core.storage import (
    append_result,
    new_run_id,
    run_path,
    runs_dir,
    write_dataset_snapshot,
    write_summary,
    write_target_snapshot,
)
from evalkit.core.target import Target, TargetError
from evalkit.evaluators.base import Evaluator


class Runner:
    """Run a dataset against a target with a set of evaluators."""

    def __init__(
        self,
        target: Target,
        evaluators: Sequence[Evaluator],
        *,
        concurrency: int = 4,
        runs_root: str | Path = "runs",
        console: Console | None = None,
    ) -> None:
        if not evaluators:
            raise ValueError("at least one evaluator is required")
        self.target = target
        self.evaluators = list(evaluators)
        self.concurrency = max(1, concurrency)
        self.runs_root = Path(runs_root)
        self.console = console or Console()
        self._evaluator_by_name: dict[str, Evaluator] = {e.name: e for e in evaluators}

    def _select_evaluators(self, case: TestCase) -> list[Evaluator]:
        if case.evaluators is None:
            return self.evaluators
        out: list[Evaluator] = []
        for name in case.evaluators:
            ev = self._evaluator_by_name.get(name)
            if ev is None:
                raise KeyError(
                    f"case {case.id!r} requested evaluator {name!r} which is not configured"
                )
            out.append(ev)
        return out

    async def _run_one(self, case: TestCase) -> CaseResult:
        t0 = time.perf_counter()
        output: Any = None
        error: str | None = None
        try:
            output = await self.target.call(case.input)
        except TargetError as e:
            error = f"target_error: {e}"
        except Exception as e:  # noqa: BLE001
            error = f"target_error: {type(e).__name__}: {e}"
        latency_ms = (time.perf_counter() - t0) * 1000.0

        evaluator_results: list[EvaluatorResult] = []
        if error is None:
            for ev in self._select_evaluators(case):
                try:
                    er = await _maybe_await(ev.evaluate(case, output))
                    evaluator_results.append(er)
                except Exception as e:  # noqa: BLE001
                    evaluator_results.append(
                        EvaluatorResult(
                            name=ev.name,
                            score=0.0,
                            passed=False,
                            reasoning=f"evaluator_error: {type(e).__name__}: {e}",
                            metadata={"error": True},
                        )
                    )

        return CaseResult(
            case_id=case.id,
            input=case.input,
            expected=case.expected,
            output=output,
            error=error,
            latency_ms=latency_ms,
            evaluators=evaluator_results,
            metadata=case.metadata,
        )

    async def run(self, dataset: Dataset, *, run_id: str | None = None) -> RunReport:
        run_id = run_id or new_run_id()
        run_dir = run_path(run_id, self.runs_root)
        run_dir.mkdir(parents=True, exist_ok=True)
        runs_dir(self.runs_root)

        write_dataset_snapshot(run_dir, dataset.source_path, list(dataset.cases))
        write_target_snapshot(run_dir, self.target.summary())

        sem = asyncio.Semaphore(self.concurrency)
        results: list[CaseResult] = []

        async def worker(case: TestCase) -> CaseResult:
            async with sem:
                r = await self._run_one(case)
                append_result(run_dir, r)
                return r

        tasks = [asyncio.create_task(worker(c)) for c in dataset.cases]

        with Progress(
            TextColumn("[bold blue]running[/bold blue]"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            console=self.console,
            transient=True,
        ) as progress:
            task_id = progress.add_task("eval", total=len(tasks))
            for coro in asyncio.as_completed(tasks):
                r = await coro
                results.append(r)
                progress.advance(task_id)

        # Preserve dataset order in the final report.
        order = {c.id: i for i, c in enumerate(dataset.cases)}
        results.sort(key=lambda r: order.get(r.case_id, 0))

        report = _aggregate(
            run_id=run_id,
            dataset=dataset,
            target_summary=self.target.summary(),
            results=results,
        )
        write_summary(run_dir, report)
        return report


async def _maybe_await(x: Any) -> Any:
    if asyncio.iscoroutine(x):
        return await x
    return x


def _aggregate(
    *,
    run_id: str,
    dataset: Dataset,
    target_summary: dict[str, Any],
    results: Iterable[CaseResult],
) -> RunReport:
    from datetime import datetime, timezone

    results = list(results)
    n = len(results)
    n_err = sum(1 for r in results if r.error is not None)
    n_pass = sum(1 for r in results if r.passed)
    n_fail = n - n_pass - n_err

    by_name: dict[str, list[EvaluatorResult]] = {}
    for r in results:
        for er in r.evaluators:
            by_name.setdefault(er.name, []).append(er)

    aggs: list[AggregateMetric] = []
    for name, ers in by_name.items():
        aggs.append(
            AggregateMetric(
                name=name,
                mean=statistics.fmean(e.score for e in ers) if ers else 0.0,
                pass_rate=sum(1 for e in ers if e.passed) / len(ers) if ers else 0.0,
                n=len(ers),
            )
        )

    latencies = [r.latency_ms for r in results if r.error is None]
    latency_stats: dict[str, float] = {}
    if latencies:
        s = sorted(latencies)
        latency_stats = {
            "mean": statistics.fmean(s),
            "p50": _quantile(s, 0.50),
            "p95": _quantile(s, 0.95),
            "p99": _quantile(s, 0.99),
            "max": s[-1],
        }

    return RunReport(
        run_id=run_id,
        finished_at=datetime.now(tz=timezone.utc),
        dataset_path=dataset.source_path or dataset.name,
        target_summary=target_summary,
        n_cases=n,
        n_passed=n_pass,
        n_failed=n_fail,
        n_errored=n_err,
        pass_rate=(n_pass / n) if n else 0.0,
        aggregate_metrics=aggs,
        latency_ms=latency_stats,
        cases=results,
        framework_version=__version__,
    )


def _quantile(sorted_xs: list[float], q: float) -> float:
    if not sorted_xs:
        return 0.0
    k = (len(sorted_xs) - 1) * q
    lo = int(k)
    hi = min(lo + 1, len(sorted_xs) - 1)
    frac = k - lo
    return sorted_xs[lo] * (1 - frac) + sorted_xs[hi] * frac
