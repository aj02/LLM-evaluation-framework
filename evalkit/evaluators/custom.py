"""Custom evaluator — wrap a user-provided callable."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from evalkit.core.case import TestCase
from evalkit.core.result import EvaluatorResult


class CustomEvaluator:
    """Adapt any callable into an Evaluator.

    The callable receives ``(case, output)`` and must return either an
    ``EvaluatorResult`` or a ``(score, passed, reasoning)`` tuple.
    """

    def __init__(
        self,
        name: str,
        fn: Callable[[TestCase, Any], EvaluatorResult | tuple[float, bool, str]],
    ) -> None:
        self.name = name
        self._fn = fn

    def evaluate(self, case: TestCase, output: Any) -> EvaluatorResult:
        result = self._fn(case, output)
        if isinstance(result, EvaluatorResult):
            return result
        try:
            score, passed, reasoning = result
        except Exception as e:  # noqa: BLE001
            raise TypeError(
                f"CustomEvaluator {self.name!r}: fn returned "
                f"{type(result).__name__}; expected EvaluatorResult or "
                f"(score, passed, reasoning) tuple"
            ) from e
        return EvaluatorResult(
            name=self.name,
            score=float(score),
            passed=bool(passed),
            reasoning=str(reasoning),
        )
