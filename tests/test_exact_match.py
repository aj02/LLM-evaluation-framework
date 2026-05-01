from __future__ import annotations

from evalkit.core.case import TestCase
from evalkit.evaluators.exact_match import ExactMatchEvaluator


def test_match_simple() -> None:
    ev = ExactMatchEvaluator()
    case = TestCase(id="a", input="x", expected="hello world")
    r = ev.evaluate(case, "Hello World")
    assert r.passed
    assert r.score == 1.0


def test_mismatch() -> None:
    ev = ExactMatchEvaluator()
    case = TestCase(id="a", input="x", expected="hello")
    r = ev.evaluate(case, "goodbye")
    assert not r.passed


def test_punctuation_normalization() -> None:
    ev = ExactMatchEvaluator(ignore_punctuation=True)
    case = TestCase(id="a", input="x", expected="hello, world!")
    r = ev.evaluate(case, "hello world")
    assert r.passed


def test_skipped_when_no_expected() -> None:
    ev = ExactMatchEvaluator()
    case = TestCase(id="a", input="x")
    r = ev.evaluate(case, "anything")
    assert not r.passed
    assert r.metadata.get("skipped") is True


def test_dict_expected_overrides_options() -> None:
    ev = ExactMatchEvaluator(ignore_case=False)
    case = TestCase(
        id="a", input="x",
        expected={"text": "Hello", "ignore_case": True},
    )
    r = ev.evaluate(case, "hello")
    assert r.passed
