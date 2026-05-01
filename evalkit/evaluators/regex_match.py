"""Regex-match evaluator: pass when the output matches a configured pattern."""
from __future__ import annotations

import re
from typing import Any

from evalkit.core.case import TestCase
from evalkit.core.result import EvaluatorResult


class RegexMatchEvaluator:
    """Pass if the output matches a regex pattern.

    The pattern can come from constructor (``pattern=...``) or from
    ``case.expected["pattern"]``. The latter takes precedence so per-case
    patterns can override defaults.
    """

    name = "regex_match"

    def __init__(self, pattern: str | None = None, *, flags: int = re.IGNORECASE) -> None:
        self.default_pattern = pattern
        self.flags = flags

    def evaluate(self, case: TestCase, output: Any) -> EvaluatorResult:
        pattern: str | None = self.default_pattern
        if isinstance(case.expected, dict) and "pattern" in case.expected:
            pattern = case.expected["pattern"]
        elif isinstance(case.expected, str) and self.default_pattern is None:
            pattern = case.expected

        if pattern is None:
            return EvaluatorResult(
                name=self.name,
                score=0.0,
                passed=False,
                reasoning="no pattern configured for this case",
                metadata={"skipped": True},
            )

        try:
            rx = re.compile(pattern, self.flags)
        except re.error as e:
            return EvaluatorResult(
                name=self.name,
                score=0.0,
                passed=False,
                reasoning=f"invalid regex {pattern!r}: {e}",
                metadata={"error": True},
            )

        produced = str(output) if output is not None else ""
        m = rx.search(produced)
        passed = m is not None
        return EvaluatorResult(
            name=self.name,
            score=1.0 if passed else 0.0,
            passed=passed,
            reasoning=(f"pattern matched {m.group(0)!r}" if m else f"pattern did not match: {pattern!r}"),
            metadata={"pattern": pattern},
        )
