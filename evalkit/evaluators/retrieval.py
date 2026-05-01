"""Retrieval metrics: recall@k, precision@k, MRR.

Designed for RAG evaluation: ``case.expected`` is the set of relevant
document ids (list of strings). ``output`` is either a list of retrieved
ids, or a dict containing one (the constructor's ``output_path`` selects
which field to read).
"""
from __future__ import annotations

from typing import Any

from evalkit.core.case import TestCase
from evalkit.core.result import EvaluatorResult


class RetrievalEvaluator:
    """Computes recall@k, precision@k, and MRR.

    The reported ``score`` is recall@k (most informative single number for
    RAG). All three metrics are stored in ``metadata`` so reports can show
    them together.
    """

    name = "retrieval"

    def __init__(
        self,
        *,
        k: int = 5,
        threshold: float = 0.6,
        output_path: str | None = "retrieved_ids",
        expected_path: str | None = "relevant_ids",
    ) -> None:
        self.k = k
        self.threshold = threshold
        self.output_path = output_path
        self.expected_path = expected_path

    @staticmethod
    def _extract(data: Any, path: str | None) -> Any:
        if path is None or not isinstance(data, dict):
            return data
        cur: Any = data
        for part in path.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return None
            cur = cur[part]
        return cur

    def evaluate(self, case: TestCase, output: Any) -> EvaluatorResult:
        retrieved = self._extract(output, self.output_path)
        relevant = self._extract(case.expected, self.expected_path)

        if not isinstance(retrieved, list):
            return EvaluatorResult(
                name=self.name,
                score=0.0,
                passed=False,
                reasoning=f"could not extract retrieved list (path={self.output_path!r})",
                metadata={"error": "missing_retrieved"},
            )
        if not isinstance(relevant, list) or not relevant:
            return EvaluatorResult(
                name=self.name,
                score=0.0,
                passed=False,
                reasoning=f"could not extract relevant list (path={self.expected_path!r})",
                metadata={"error": "missing_relevant", "skipped": True},
            )

        retrieved_topk = [str(x) for x in retrieved[: self.k]]
        relevant_set = {str(x) for x in relevant}

        hits = sum(1 for r in retrieved_topk if r in relevant_set)
        recall = hits / len(relevant_set) if relevant_set else 0.0
        precision = hits / len(retrieved_topk) if retrieved_topk else 0.0

        mrr = 0.0
        for rank, doc_id in enumerate(retrieved_topk, start=1):
            if doc_id in relevant_set:
                mrr = 1.0 / rank
                break

        passed = recall >= self.threshold
        return EvaluatorResult(
            name=self.name,
            score=recall,
            passed=passed,
            reasoning=(
                f"recall@{self.k}={recall:.2f} precision@{self.k}={precision:.2f} mrr={mrr:.2f}"
            ),
            metadata={
                "k": self.k,
                f"recall@{self.k}": recall,
                f"precision@{self.k}": precision,
                "mrr": mrr,
                "hits": hits,
                "n_relevant": len(relevant_set),
                "n_retrieved": len(retrieved_topk),
                "threshold": self.threshold,
            },
        )
