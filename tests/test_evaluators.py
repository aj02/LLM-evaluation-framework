from __future__ import annotations

from evalkit.core.case import TestCase
from evalkit.evaluators.custom import CustomEvaluator
from evalkit.evaluators.latency import LatencyEvaluator
from evalkit.evaluators.regex_match import RegexMatchEvaluator
from evalkit.evaluators.retrieval import RetrievalEvaluator


# ---------------------------------------------------------------------------
# regex_match
# ---------------------------------------------------------------------------
def test_regex_match_default_pattern() -> None:
    ev = RegexMatchEvaluator(pattern=r"^hello\b")
    case = TestCase(id="a", input="x")
    assert ev.evaluate(case, "hello there").passed
    assert not ev.evaluate(case, "goodbye").passed


def test_regex_match_per_case_pattern_overrides() -> None:
    ev = RegexMatchEvaluator(pattern=r"foo")
    case = TestCase(id="a", input="x", expected={"pattern": r"\d+"})
    r = ev.evaluate(case, "answer is 42")
    assert r.passed
    assert r.metadata["pattern"] == r"\d+"


def test_regex_match_invalid_pattern() -> None:
    ev = RegexMatchEvaluator(pattern=r"(unbalanced")
    case = TestCase(id="a", input="x")
    r = ev.evaluate(case, "anything")
    assert not r.passed
    assert r.metadata.get("error")


def test_regex_match_no_pattern_skips() -> None:
    ev = RegexMatchEvaluator()
    case = TestCase(id="a", input="x")
    r = ev.evaluate(case, "anything")
    assert r.metadata.get("skipped")


# ---------------------------------------------------------------------------
# retrieval
# ---------------------------------------------------------------------------
def test_retrieval_recall_precision_mrr() -> None:
    ev = RetrievalEvaluator(k=5, threshold=0.5)
    case = TestCase(
        id="rag1",
        input={"q": "what is X?"},
        expected={"relevant_ids": ["doc_a", "doc_b"]},
    )
    r = ev.evaluate(case, {"retrieved_ids": ["doc_a", "doc_x", "doc_b", "doc_y", "doc_z"]})
    # 2/2 relevant retrieved → recall = 1.0
    assert r.score == 1.0
    assert r.passed
    assert r.metadata["recall@5"] == 1.0
    # 2 hits in 5 retrieved → precision = 0.4
    assert r.metadata["precision@5"] == 0.4
    # First hit at rank 1
    assert r.metadata["mrr"] == 1.0


def test_retrieval_partial_recall() -> None:
    ev = RetrievalEvaluator(k=3, threshold=0.5)
    case = TestCase(
        id="rag2",
        input={},
        expected={"relevant_ids": ["a", "b", "c", "d"]},
    )
    r = ev.evaluate(case, {"retrieved_ids": ["x", "a", "y"]})
    # 1 of 4 relevant retrieved → recall = 0.25
    assert r.metadata["recall@3"] == 0.25
    # MRR: first hit at rank 2 → 0.5
    assert r.metadata["mrr"] == 0.5
    assert not r.passed


def test_retrieval_missing_relevant_skipped() -> None:
    ev = RetrievalEvaluator()
    case = TestCase(id="rag3", input={}, expected={})
    r = ev.evaluate(case, {"retrieved_ids": ["a"]})
    assert r.metadata.get("skipped")


def test_retrieval_no_retrieval_field_errors() -> None:
    ev = RetrievalEvaluator()
    case = TestCase(id="rag4", input={}, expected={"relevant_ids": ["a"]})
    r = ev.evaluate(case, {"some_other_field": []})
    assert not r.passed
    assert r.metadata["error"] == "missing_retrieved"


# ---------------------------------------------------------------------------
# latency
# ---------------------------------------------------------------------------
def test_latency_no_budget_passes() -> None:
    ev = LatencyEvaluator()
    case = TestCase(id="x", input={})
    r = ev.evaluate(case, "anything")
    assert r.passed
    assert r.metadata.get("skipped")


def test_latency_with_budget() -> None:
    ev = LatencyEvaluator()
    case = TestCase(id="x", input={}, metadata={"latency_budget_ms": 500.0})
    r = ev.evaluate(case, "anything")
    assert r.metadata["budget_ms"] == 500.0


# ---------------------------------------------------------------------------
# custom evaluator
# ---------------------------------------------------------------------------
def test_custom_evaluator_tuple_return() -> None:
    ev = CustomEvaluator("len_check", lambda c, o: (1.0 if len(str(o)) >= 3 else 0.0,
                                                     len(str(o)) >= 3,
                                                     f"len={len(str(o))}"))
    case = TestCase(id="a", input="x")
    r = ev.evaluate(case, "hi!")
    assert r.passed
    assert r.score == 1.0
