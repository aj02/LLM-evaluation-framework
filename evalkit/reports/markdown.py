"""Markdown report generator."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from evalkit.core.result import RunReport

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def _render_inline(value: Any) -> str:
    """Render any value as a single-line, markdown-safe string."""
    if value is None:
        return "*(none)*"
    if isinstance(value, str):
        return value.replace("\n", " ").replace("|", "\\|")
    try:
        return json.dumps(value, ensure_ascii=False).replace("|", "\\|")
    except (TypeError, ValueError):
        return str(value).replace("\n", " ").replace("|", "\\|")


def _build_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(default_for_string=False, default=False),
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
    )
    env.filters["render_inline"] = _render_inline
    return env


def render_markdown(report: RunReport, out_path: str | Path) -> Path:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    env = _build_env()
    template = env.get_template("report.md.j2")

    failed_cases = [c for c in report.cases if not c.passed]

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

    text = template.render(
        report=report,
        failed_cases=failed_cases,
        total_cost=total_cost,
        total_in_tokens=total_in,
        total_out_tokens=total_out,
    )
    p.write_text(text, encoding="utf-8")
    return p
