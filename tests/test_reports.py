from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from evalkit.core.result import (
    AggregateMetric,
    CaseResult,
    EvaluatorResult,
    RunReport,
)
from evalkit.reports.html import render_dashboard
from evalkit.reports.json_export import write_json_report
from evalkit.reports.markdown import render_markdown


def _make_report() -> RunReport:
    cases = [
        CaseResult(
            case_id="ok",
            input={"q": "hi"},
            expected="HI",
            output="HI",
            latency_ms=12.3,
            evaluators=[EvaluatorResult(name="exact_match", score=1.0, passed=True, reasoning="match")],
            metadata={"category": "smoke"},
        ),
        CaseResult(
            case_id="bad",
            input={"q": "world"},
            expected="WORLD",
            output="hello",
            latency_ms=22.0,
            evaluators=[EvaluatorResult(name="exact_match", score=0.0, passed=False, reasoning="mismatch")],
            metadata={"category": "smoke"},
        ),
        CaseResult(
            case_id="boom",
            input={"q": "x"},
            expected=None,
            output=None,
            error="target_error: boom",
            latency_ms=0.0,
            evaluators=[],
        ),
    ]
    return RunReport(
        run_id="20260501T120000Z__deadbeef",
        started_at=datetime.now(tz=timezone.utc),
        finished_at=datetime.now(tz=timezone.utc),
        dataset_path="/tmp/x.jsonl",
        target_summary={"name": "test", "type": "CallableTarget"},
        n_cases=3,
        n_passed=1,
        n_failed=1,
        n_errored=1,
        pass_rate=1.0/3,
        aggregate_metrics=[AggregateMetric(name="exact_match", mean=0.5, pass_rate=0.5, n=2)],
        latency_ms={"mean": 17.0, "p50": 12.3, "p95": 22.0, "p99": 22.0},
        cases=cases,
        framework_version="0.1.0",
    )


def test_markdown_renders(tmp_path: Path) -> None:
    rep = _make_report()
    p = render_markdown(rep, tmp_path / "report.md")
    text = p.read_text(encoding="utf-8")
    assert "20260501T120000Z__deadbeef" in text
    # summary numbers
    assert "33.3%" in text  # pass rate
    # Failed cases section should reference both bad and boom
    assert "bad" in text
    assert "boom" in text
    # All cases table should have all three rows
    for cid in ("ok", "bad", "boom"):
        assert cid in text


def test_html_renders(tmp_path: Path) -> None:
    rep = _make_report()
    p = render_dashboard(rep, tmp_path / "dash.html")
    text = p.read_text(encoding="utf-8")
    assert "<!doctype html>" in text.lower()
    assert "20260501T120000Z__deadbeef" in text
    assert "exact_match" in text


def test_html_with_comparison(tmp_path: Path) -> None:
    prev = _make_report()
    prev.run_id = "20260501T100000Z__cafebabe"
    prev.aggregate_metrics = [AggregateMetric(name="exact_match", mean=0.7, pass_rate=0.7, n=2)]
    prev.pass_rate = 0.5
    rep = _make_report()
    p = render_dashboard(rep, tmp_path / "dash.html", previous=prev)
    text = p.read_text(encoding="utf-8")
    # Should contain the delta column header
    assert "Δ mean" in text
    # And the pass-rate delta card
    assert "previous" in text


def test_json_export(tmp_path: Path) -> None:
    import json
    rep = _make_report()
    p = write_json_report(rep, tmp_path / "report.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["run_id"] == "20260501T120000Z__deadbeef"
    assert len(data["cases"]) == 3
