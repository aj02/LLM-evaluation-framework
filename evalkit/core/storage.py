"""Local filesystem run storage.

Layout::

    runs/
      20260501T120000Z__abcd1234/
        dataset.json
        target.json
        results.jsonl
        summary.json
        report.md
        dashboard.html
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evalkit.core.case import TestCase
from evalkit.core.result import CaseResult, RunReport

RUN_ID_RE = re.compile(r"^\d{8}T\d{6}Z__[a-f0-9]{8}$")


def new_run_id() -> str:
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{ts}__{uuid.uuid4().hex[:8]}"


def runs_dir(root: str | Path = "runs") -> Path:
    p = Path(root)
    p.mkdir(parents=True, exist_ok=True)
    return p


def run_path(run_id: str, root: str | Path = "runs") -> Path:
    return runs_dir(root) / run_id


def write_dataset_snapshot(
    run_dir: Path, dataset_path: str | None, cases: list[TestCase]
) -> None:
    payload = {
        "source_path": dataset_path,
        "n_cases": len(cases),
        "cases": [c.model_dump(mode="json") for c in cases],
    }
    (run_dir / "dataset.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


def write_target_snapshot(run_dir: Path, target_summary: dict[str, Any]) -> None:
    (run_dir / "target.json").write_text(
        json.dumps(target_summary, indent=2), encoding="utf-8"
    )


def append_result(run_dir: Path, result: CaseResult) -> None:
    line = json.dumps(result.model_dump(mode="json"), ensure_ascii=False)
    with (run_dir / "results.jsonl").open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def write_summary(run_dir: Path, report: RunReport) -> None:
    payload = report.model_dump(mode="json", exclude={"cases"})
    (run_dir / "summary.json").write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8"
    )


def load_report(run_id: str, root: str | Path = "runs") -> RunReport:
    rdir = run_path(run_id, root)
    if not rdir.exists():
        raise FileNotFoundError(f"run not found: {run_id}")
    summary = json.loads((rdir / "summary.json").read_text(encoding="utf-8"))
    cases: list[CaseResult] = []
    results_path = rdir / "results.jsonl"
    if results_path.exists():
        with results_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    cases.append(CaseResult.model_validate_json(line))
    summary["cases"] = [c.model_dump(mode="json") for c in cases]
    return RunReport.model_validate(summary)


def list_runs(root: str | Path = "runs", limit: int = 50) -> list[str]:
    p = Path(root)
    if not p.exists():
        return []
    entries = [d.name for d in p.iterdir() if d.is_dir() and RUN_ID_RE.match(d.name)]
    entries.sort(reverse=True)
    return entries[:limit]
