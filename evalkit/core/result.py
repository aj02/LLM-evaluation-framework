"""Result models — what comes out of a run."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EvaluatorResult(BaseModel):
    """Output of a single evaluator on a single case."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Evaluator name (e.g. 'exact_match').")
    score: float = Field(..., ge=0.0, le=1.0, description="Normalized score in [0, 1].")
    passed: bool = Field(..., description="Boolean pass/fail (evaluator-defined threshold).")
    reasoning: str = Field(default="", description="Human-readable rationale.")
    metadata: dict[str, Any] = Field(default_factory=dict)


class CaseResult(BaseModel):
    """Result of running one TestCase end-to-end."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    input: Any
    expected: Any | None = None
    output: Any | None = None
    error: str | None = None
    latency_ms: float = 0.0
    evaluators: list[EvaluatorResult] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """A case passes if it produced output AND every evaluator passed."""
        return self.error is None and bool(self.evaluators) and all(e.passed for e in self.evaluators)


class AggregateMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    mean: float
    pass_rate: float
    n: int


class RunReport(BaseModel):
    """Top-level summary of a run."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    finished_at: datetime | None = None
    dataset_path: str
    target_summary: dict[str, Any]
    n_cases: int
    n_passed: int
    n_failed: int
    n_errored: int
    pass_rate: float
    aggregate_metrics: list[AggregateMetric] = Field(default_factory=list)
    latency_ms: dict[str, float] = Field(default_factory=dict)
    cases: list[CaseResult] = Field(default_factory=list)
    framework_version: str = ""
