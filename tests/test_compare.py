from __future__ import annotations

from datetime import datetime, timezone

from evalkit.core.compare import compare_runs, format_comparison_markdown, format_comparison_table
from evalkit.core.result import (
    AggregateMetric,
    CaseResult,
    EvaluatorResult,
    RunReport,
)


def _result(case_id: str, passed: bool, score: float = 1.0) -> CaseResult:
    return CaseResult(
        case_id=case_id,
        input={"q": case_id},
        expected="x",
        output="x" if passed else "y",
        latency_ms=10.0,
        evaluators=[EvaluatorResult(
            name="exact_match", score=score, passed=passed, reasoning=""
        )],
    )


def _report(run_id: str, cases: list[CaseResult], mean: float, pass_rate: float,
            latency: dict[str, float] | None = None) -> RunReport:
    return RunReport(
        run_id=run_id,
        started_at=datetime.now(tz=timezone.utc),
        finished_at=datetime.now(tz=timezone.utc),
        dataset_path="x.jsonl",
        target_summary={"name": "t", "type": "CallableTarget"},
        n_cases=len(cases),
        n_passed=sum(1 for c in cases if c.passed),
        n_failed=sum(1 for c in cases if not c.passed and not c.error),
        n_errored=sum(1 for c in cases if c.error),
        pass_rate=pass_rate,
        aggregate_metrics=[AggregateMetric(name="exact_match", mean=mean,
                                           pass_rate=pass_rate, n=len(cases))],
        latency_ms=latency or {},
        cases=cases,
        framework_version="0.1.0",
    )


def test_compare_no_change() -> None:
    a = _report("a", [_result("c1", True), _result("c2", True)], 1.0, 1.0)
    b = _report("b", [_result("c1", True), _result("c2", True)], 1.0, 1.0)
    diff = compare_runs(a, b)
    assert diff.delta_pass_rate == 0
    assert diff.flips == []


def test_compare_detects_regression_flip() -> None:
    a = _report("a", [_result("c1", True), _result("c2", True)], 1.0, 1.0)
    b = _report("b", [_result("c1", True), _result("c2", False, 0.0)], 0.5, 0.5)
    diff = compare_runs(a, b)
    assert diff.delta_pass_rate == -0.5
    assert len(diff.flips) == 1
    assert diff.flips[0].case_id == "c2"
    assert diff.flips[0].direction == "regressed"


def test_compare_detects_improvement_flip() -> None:
    a = _report("a", [_result("c1", False, 0.0)], 0.0, 0.0)
    b = _report("b", [_result("c1", True)], 1.0, 1.0)
    diff = compare_runs(a, b)
    assert diff.flips[0].direction == "improved"


def test_compare_handles_disjoint_case_sets() -> None:
    a = _report("a", [_result("c1", True), _result("c2", True)], 1.0, 1.0)
    b = _report("b", [_result("c1", True), _result("c3", True)], 1.0, 1.0)
    diff = compare_runs(a, b)
    assert diff.cases_only_in_a == ["c2"]
    assert diff.cases_only_in_b == ["c3"]


def test_compare_latency_delta() -> None:
    a = _report("a", [_result("c1", True)], 1.0, 1.0,
                latency={"p50": 100.0, "p95": 200.0})
    b = _report("b", [_result("c1", True)], 1.0, 1.0,
                latency={"p50": 90.0, "p95": 180.0})
    diff = compare_runs(a, b)
    assert diff.latency_delta["p50"] == -10.0
    assert diff.latency_delta["p95"] == -20.0


def test_compare_evaluator_deltas() -> None:
    a = _report("a", [_result("c1", True, 1.0), _result("c2", True, 1.0)], 1.0, 1.0)
    b = _report("b", [_result("c1", True, 0.6), _result("c2", False, 0.0)], 0.3, 0.5)
    diff = compare_runs(a, b)
    em = next(d for d in diff.evaluator_deltas if d.name == "exact_match")
    assert em.delta_mean < 0
    assert em.delta_pass_rate < 0


def test_format_table_includes_key_lines() -> None:
    a = _report("a", [_result("c1", True)], 1.0, 1.0)
    b = _report("b", [_result("c1", False, 0.0)], 0.0, 0.0)
    text = format_comparison_table(compare_runs(a, b))
    assert "compare:" in text
    assert "flips" in text


def test_format_markdown_table() -> None:
    a = _report("a", [_result("c1", True)], 1.0, 1.0)
    b = _report("b", [_result("c1", False, 0.0)], 0.0, 0.0)
    text = format_comparison_markdown(compare_runs(a, b))
    assert "| `exact_match` |" in text
    assert "Flips" in text
