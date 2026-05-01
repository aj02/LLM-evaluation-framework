"""Semantic similarity via sentence-transformers (lazy import)."""
from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Any

from evalkit.core.case import TestCase
from evalkit.core.result import EvaluatorResult

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=4)
def _load_model(model_name: str) -> SentenceTransformer:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise ImportError(
            "semantic_similarity requires the 'semantic' extra: "
            "pip install evalkit[semantic]"
        ) from e
    return SentenceTransformer(model_name)


def _cosine(a: list[float], b: list[float]) -> float:
    import math
    if len(a) != len(b):
        raise ValueError("vectors must have the same length")
    num = sum(x * y for x, y in zip(a, b, strict=True))
    da = math.sqrt(sum(x * x for x in a))
    db = math.sqrt(sum(y * y for y in b))
    if da == 0.0 or db == 0.0:
        return 0.0
    return num / (da * db)


class SemanticSimilarityEvaluator:
    """Cosine similarity between expected and output embeddings.

    Only loads the model on first call (lazy). Score in [0, 1] (clamped from
    cosine). ``threshold`` is the pass cutoff."""

    name = "semantic_similarity"

    def __init__(
        self,
        *,
        model: str = "sentence-transformers/all-MiniLM-L6-v2",
        threshold: float = 0.75,
    ) -> None:
        self.model_name = model
        self.threshold = threshold

    def _embed(self, texts: list[str]) -> list[list[float]]:
        model = _load_model(self.model_name)
        vecs = model.encode(texts, normalize_embeddings=False, convert_to_numpy=False)
        return [list(map(float, v)) for v in vecs]

    def evaluate(self, case: TestCase, output: Any) -> EvaluatorResult:
        if case.expected is None:
            return EvaluatorResult(
                name=self.name,
                score=0.0,
                passed=False,
                reasoning="no expected value to compare against",
                metadata={"skipped": True},
            )

        expected_text = case.expected if isinstance(case.expected, str) else str(case.expected)
        produced = str(output) if output is not None else ""
        if not produced.strip():
            return EvaluatorResult(
                name=self.name,
                score=0.0,
                passed=False,
                reasoning="empty output",
            )

        e_vec, p_vec = self._embed([expected_text, produced])
        sim = _cosine(e_vec, p_vec)
        score = max(0.0, min(1.0, (sim + 1.0) / 2.0))  # map [-1, 1] -> [0, 1]
        passed = sim >= self.threshold
        return EvaluatorResult(
            name=self.name,
            score=score,
            passed=passed,
            reasoning=f"cosine={sim:.3f} threshold={self.threshold:.2f}",
            metadata={"cosine": sim, "model": self.model_name, "threshold": self.threshold},
        )
