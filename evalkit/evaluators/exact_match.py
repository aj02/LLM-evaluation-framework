"""Exact-match evaluator (string equality with optional normalization)."""
from __future__ import annotations

import re
from typing import Any

from evalkit.core.case import TestCase
from evalkit.core.result import EvaluatorResult


class ExactMatchEvaluator:
    """Compares the target output to ``case.expected`` after normalization.

    The expected value can either be a plain string, or a dict like
    ``{"text": "...", "ignore_case": true, "ignore_punctuation": true}``.
    Non-string outputs are coerced via ``str(output).strip()``.
    """

    name = "exact_match"

    def __init__(
        self,
        *,
        ignore_case: bool = True,
        ignore_punctuation: bool = False,
        strip_whitespace: bool = True,
    ) -> None:
        self.ignore_case = ignore_case
        self.ignore_punctuation = ignore_punctuation
        self.strip_whitespace = strip_whitespace

    def _normalize(self, s: str, *, ignore_case: bool, ignore_punctuation: bool) -> str:
        if self.strip_whitespace:
            s = s.strip()
        if ignore_case:
            s = s.lower()
        if ignore_punctuation:
            s = re.sub(r"[^\w\s]", "", s)
        # collapse internal whitespace
        s = re.sub(r"\s+", " ", s)
        return s

    def evaluate(self, case: TestCase, output: Any) -> EvaluatorResult:
        if case.expected is None:
            return EvaluatorResult(
                name=self.name,
                score=0.0,
                passed=False,
                reasoning="no expected value provided; cannot exact-match",
                metadata={"skipped": True},
            )

        ic, ip = self.ignore_case, self.ignore_punctuation
        if isinstance(case.expected, dict) and "text" in case.expected:
            target = str(case.expected["text"])
            ic = bool(case.expected.get("ignore_case", ic))
            ip = bool(case.expected.get("ignore_punctuation", ip))
        else:
            target = str(case.expected)

        produced = str(output) if output is not None else ""

        a = self._normalize(target, ignore_case=ic, ignore_punctuation=ip)
        b = self._normalize(produced, ignore_case=ic, ignore_punctuation=ip)
        passed = a == b
        return EvaluatorResult(
            name=self.name,
            score=1.0 if passed else 0.0,
            passed=passed,
            reasoning=("strings match after normalization" if passed
                       else f"mismatch: expected={a!r} got={b!r}"),
            metadata={"ignore_case": ic, "ignore_punctuation": ip},
        )
