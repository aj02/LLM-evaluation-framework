"""LLM provider interface — small, swappable, JSON-mode focused."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


@dataclass(frozen=True)
class LLMResponse:
    text: str
    usage: LLMUsage
    model: str
    provider: str
    raw: object | None = None


class LLMClient(ABC):
    """Minimal client surface — sync wrapping is fine, calls are I/O-bound
    and the runner already provides concurrency at the case level."""

    provider: str
    model: str

    @abstractmethod
    def complete_json(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Return a model response. Caller is responsible for JSON parsing.

        Implementations should encourage strict JSON output via system prompt
        / response_format hints, but must NOT silently parse — bubble up the
        text and let the caller validate against a Pydantic schema so the
        judge can recover from malformed output.
        """
