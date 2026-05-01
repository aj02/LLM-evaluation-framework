"""Comparison logic for two RunReports — full impl in step 7."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from evalkit.core.result import RunReport


class CaseFlip(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    direction: str  # "improved" or "regressed"
    a_passed: bool
    b_passed: bool
    a_score: float | None = None
    b_score: float | None = None


class EvaluatorDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    mean_a: float
    mean_b: float
    delta_mean: float
    pass_rate_a: float
    pass_rate_b: float
    delta_pass_rate: float
    n: int


class ComparisonReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_a: str
    run_b: str
    pass_rate_a: float
    pass_rate_b: float
    delta_pass_rate: float
    evaluator_deltas: list[EvaluatorDelta] = Field(default_factory=list)
    flips: list[CaseFlip] = Field(default_factory=list)
    cases_only_in_a: list[str] = Field(default_factory=list)
    cases_only_in_b: list[str] = Field(default_factory=list)
    latency_delta: dict[str, float] = Field(default_factory=dict)


def compare_runs(a: RunReport, b: RunReport) -> ComparisonReport:
    a_cases = {c.case_id: c for c in a.cases}
    b_cases = {c.case_id: c for c in b.cases}
    common_ids = sorted(set(a_cases) & set(b_cases))

    a_aggs = {m.name: m for m in a.aggregate_metrics}
    b_aggs = {m.name: m for m in b.aggregate_metrics}

    eval_deltas: list[EvaluatorDelta] = []
    for name in sorted(set(a_aggs) | set(b_aggs)):
        ma = a_aggs.get(name)
        mb = b_aggs.get(name)
        mean_a = ma.mean if ma else 0.0
        mean_b = mb.mean if mb else 0.0
        pr_a = ma.pass_rate if ma else 0.0
        pr_b = mb.pass_rate if mb else 0.0
        n = max(ma.n if ma else 0, mb.n if mb else 0)
        eval_deltas.append(
            EvaluatorDelta(
                name=name,
                mean_a=mean_a, mean_b=mean_b, delta_mean=mean_b - mean_a,
                pass_rate_a=pr_a, pass_rate_b=pr_b, delta_pass_rate=pr_b - pr_a,
                n=n,
            )
        )

    flips: list[CaseFlip] = []
    for cid in common_ids:
        ca, cb = a_cases[cid], b_cases[cid]
        if ca.passed != cb.passed:
            sa = _avg_score(ca.evaluators)
            sb = _avg_score(cb.evaluators)
            flips.append(
                CaseFlip(
                    case_id=cid,
                    direction="improved" if cb.passed else "regressed",
                    a_passed=ca.passed,
                    b_passed=cb.passed,
                    a_score=sa,
                    b_score=sb,
                )
            )

    latency_delta: dict[str, float] = {}
    for k in ("p50", "p95", "p99", "mean"):
        if k in a.latency_ms and k in b.latency_ms:
            latency_delta[k] = b.latency_ms[k] - a.latency_ms[k]

    return ComparisonReport(
        run_a=a.run_id,
        run_b=b.run_id,
        pass_rate_a=a.pass_rate,
        pass_rate_b=b.pass_rate,
        delta_pass_rate=b.pass_rate - a.pass_rate,
        evaluator_deltas=eval_deltas,
        flips=flips,
        cases_only_in_a=sorted(set(a_cases) - set(b_cases)),
        cases_only_in_b=sorted(set(b_cases) - set(a_cases)),
        latency_delta=latency_delta,
    )


def _avg_score(evaluators: list[Any]) -> float | None:
    if not evaluators:
        return None
    return sum(e.score for e in evaluators) / len(evaluators)


def format_comparison_table(diff: ComparisonReport) -> str:
    """ASCII-only formatting — this string is destined for stdout, and legacy
    Windows consoles can't render Greek delta even via rich."""
    lines = []
    lines.append(f"compare: {diff.run_a} -> {diff.run_b}")
    lines.append(
        f"pass rate: {diff.pass_rate_a*100:.1f}% -> {diff.pass_rate_b*100:.1f}% "
        f"(d {diff.delta_pass_rate*100:+.1f}pp)"
    )
    lines.append("")
    lines.append("evaluator deltas:")
    for d in diff.evaluator_deltas:
        lines.append(
            f"  {d.name:<22} mean {d.mean_a:.3f} -> {d.mean_b:.3f} "
            f"(d{d.delta_mean:+.3f})  pass% {d.pass_rate_a*100:5.1f} -> {d.pass_rate_b*100:5.1f} "
            f"(d{d.delta_pass_rate*100:+.1f}pp)  n={d.n}"
        )
    if diff.flips:
        lines.append("")
        lines.append(f"flips ({len(diff.flips)}):")
        for f in diff.flips:
            arrow = "+" if f.direction == "improved" else "-"
            lines.append(f"  [{arrow}] {f.case_id:<30} {f.a_passed} -> {f.b_passed}")
    if diff.latency_delta:
        lines.append("")
        lines.append("latency delta (ms):")
        for k, v in diff.latency_delta.items():
            lines.append(f"  {k:<5} {v:+.1f}")
    return "\n".join(lines)


def format_comparison_markdown(diff: ComparisonReport) -> str:
    lines = []
    lines.append(f"# Comparison — `{diff.run_a}` vs `{diff.run_b}`")
    lines.append("")
    lines.append(
        f"**Pass rate:** {diff.pass_rate_a*100:.1f}% → {diff.pass_rate_b*100:.1f}% "
        f"(Δ {diff.delta_pass_rate*100:+.1f}pp)"
    )
    lines.append("")
    lines.append("## Evaluator deltas")
    lines.append("")
    lines.append("| evaluator | mean A | mean B | Δ mean | pass A | pass B | Δ pass | n |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for d in diff.evaluator_deltas:
        lines.append(
            f"| `{d.name}` | {d.mean_a:.3f} | {d.mean_b:.3f} | {d.delta_mean:+.3f} "
            f"| {d.pass_rate_a*100:.1f}% | {d.pass_rate_b*100:.1f}% "
            f"| {d.delta_pass_rate*100:+.1f}pp | {d.n} |"
        )
    if diff.flips:
        lines.append("")
        lines.append(f"## Flips ({len(diff.flips)})")
        lines.append("")
        lines.append("| case | direction | A | B |")
        lines.append("|---|---|---|---|")
        for f in diff.flips:
            lines.append(f"| `{f.case_id}` | {f.direction} | {f.a_passed} | {f.b_passed} |")
    if diff.latency_delta:
        lines.append("")
        lines.append("## Latency delta")
        lines.append("")
        for k, v in diff.latency_delta.items():
            lines.append(f"- **{k}**: {v:+.1f} ms")
    return "\n".join(lines) + "\n"
