from __future__ import annotations

import pytest
from pydantic import ValidationError

from evalkit.core.case import TestCase


def test_minimal_case_validates() -> None:
    c = TestCase(id="x", input={"q": "hi"})
    assert c.id == "x"
    assert c.expected is None
    assert c.metadata == {}
    assert c.evaluators is None


def test_id_no_whitespace() -> None:
    with pytest.raises(ValidationError):
        TestCase(id="bad id", input={})


def test_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        TestCase(id="x", input={}, oops=1)


def test_immutable() -> None:
    c = TestCase(id="x", input={"q": "hi"})
    with pytest.raises(ValidationError):
        c.id = "y"  # type: ignore[misc]
