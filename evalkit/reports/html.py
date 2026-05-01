"""HTML dashboard generator with optional previous-run comparison."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from evalkit.core.compare import compare_runs
from evalkit.core.result import RunReport

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def _safe_tojson(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return str(value)


def _build_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(default_for_string=True, default=True),
        keep_trailing_newline=True,
    )
    env.filters["tojson"] = _safe_tojson
    return env


def render_dashboard(
    report: RunReport,
    out_path: str | Path,
    *,
    previous: RunReport | None = None,
) -> Path:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    env = _build_env()
    template = env.get_template("dashboard.html.j2")

    comparison = None
    comparison_by_name: dict[str, Any] = {}
    if previous is not None:
        comparison = compare_runs(previous, report)
        comparison_by_name = {d.name: d for d in comparison.evaluator_deltas}

    total_cost = 0.0
    total_in = 0
    total_out = 0
    for c in report.cases:
        for ev in c.evaluators:
            for key in ("usage_pass1", "usage_pass2"):
                u = ev.metadata.get(key)
                if isinstance(u, dict):
                    total_cost += float(u.get("cost_usd", 0) or 0)
                    total_in += int(u.get("input_tokens", 0) or 0)
                    total_out += int(u.get("output_tokens", 0) or 0)

    html = template.render(
        report=report,
        comparison=comparison,
        comparison_by_name=comparison_by_name,
        total_cost=total_cost,
        total_in_tokens=total_in,
        total_out_tokens=total_out,
    )
    p.write_text(html, encoding="utf-8")
    return p
