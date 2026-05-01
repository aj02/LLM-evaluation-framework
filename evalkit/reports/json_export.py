"""Full JSON export of a RunReport (including all per-case data)."""
from __future__ import annotations

import json
from pathlib import Path

from evalkit.core.result import RunReport


def write_json_report(report: RunReport, out_path: str | Path) -> Path:
    p = Path(out_path)
    p.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, default=str),
        encoding="utf-8",
    )
    return p
