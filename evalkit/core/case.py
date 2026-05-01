"""TestCase — the atomic unit of an evaluation dataset."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TestCase(BaseModel):
    """A single test case.

    The schema is intentionally loose on `input`/`expected` so the framework
    can target any system whose interface is "give me JSON, get JSON back."
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    __test__ = False  # tell pytest not to auto-collect this as a test class

    id: str = Field(..., min_length=1, description="Unique case identifier within a dataset.")
    input: Any = Field(..., description="Arbitrary JSON passed to the target.")
    expected: Any | None = Field(
        default=None,
        description="Optional expected output, consumed by evaluators.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Free-form tags: category, difficulty, source, etc.",
    )
    evaluators: list[str] | None = Field(
        default=None,
        description="If set, only these evaluator names are applied to this case.",
    )

    @field_validator("id")
    @classmethod
    def _no_whitespace_id(cls, v: str) -> str:
        if any(ch.isspace() for ch in v):
            raise ValueError("TestCase.id must not contain whitespace")
        return v
