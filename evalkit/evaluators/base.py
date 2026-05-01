"""Evaluator interface."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from evalkit.core.case import TestCase
from evalkit.core.result import EvaluatorResult


@runtime_checkable
class Evaluator(Protocol):
    """An evaluator scores a target's output for a given test case.

    Implementations should be pure (no side effects), idempotent on identical
    inputs, and report ``passed=False`` when the case has no signal rather
    than raising — the runner reserves exceptions for "this evaluator broke."
    """

    name: str

    def evaluate(self, case: TestCase, output: Any) -> EvaluatorResult: ...
