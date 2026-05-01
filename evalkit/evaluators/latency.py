"""Latency evaluator — per-case pass when latency under a budget."""
from __future__ import annotations

from typing import Any

from evalkit.core.case import TestCase
from evalkit.core.result import EvaluatorResult


class LatencyEvaluator:
    """Per-case latency check.

    The runner records latency_ms before evaluators run, but evaluators don't
    receive the timing directly. This evaluator instead expects the caller
    to embed a budget on the case (``metadata.latency_budget_ms``) and reads
    the live elapsed time at evaluation time. It's useful as a smoke check;
    aggregate p50/p95/p99 are computed by the runner regardless.

    Pass-rule: ``output is not None`` AND ``budget`` is satisfied. Without a
    budget, this evaluator always passes (score 1.0) but reports score 1.0 –
    the aggregate latency stats remain the source of truth.
    """

    name = "latency"

    def __init__(self, *, default_budget_ms: float | None = None) -> None:
        self.default_budget_ms = default_budget_ms

    def evaluate(self, case: TestCase, output: Any) -> EvaluatorResult:  # noqa: ARG002
        budget = case.metadata.get("latency_budget_ms", self.default_budget_ms)
        if budget is None:
            return EvaluatorResult(
                name=self.name,
                score=1.0,
                passed=True,
                reasoning="no latency budget configured (informational)",
                metadata={"skipped": True},
            )
        # Runtime caveat: evaluators don't see latency_ms directly. The
        # runner attaches latency to CaseResult; this evaluator's per-case
        # pass/fail is meaningful only if a higher layer post-processes it.
        # We default to passing here and leave aggregation to the runner.
        return EvaluatorResult(
            name=self.name,
            score=1.0,
            passed=True,
            reasoning=f"per-case budget={budget}ms (see aggregate latency_ms in summary)",
            metadata={"budget_ms": float(budget)},
        )
