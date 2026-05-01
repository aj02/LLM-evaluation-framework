"""Anthropic implementation."""
from __future__ import annotations

import os

from evalkit.llm.base import LLMClient, LLMResponse, LLMUsage

# Approx pricing (USD per 1M tokens) — used for ballpark cost tracking.
# Update as Anthropic publishes new tiers.
_PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-4-7": (15.00, 75.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "claude-sonnet-4-5": (3.00, 15.00),
}


def _cost(model: str, in_t: int, out_t: int) -> float:
    if model not in _PRICING:
        return 0.0
    in_per_m, out_per_m = _PRICING[model]
    return (in_t / 1_000_000) * in_per_m + (out_t / 1_000_000) * out_per_m


class AnthropicClient(LLMClient):
    provider = "anthropic"

    def __init__(
        self,
        *,
        model: str = "claude-sonnet-4-6",
        api_key: str | None = None,
    ) -> None:
        try:
            from anthropic import Anthropic
        except ImportError as e:
            raise ImportError("anthropic package is required") from e
        self.model = model
        self._client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> LLMResponse:
        msg = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text_blocks = [
            getattr(b, "text", "") for b in msg.content if getattr(b, "type", "") == "text"
        ]
        text = "".join(text_blocks)
        in_t = msg.usage.input_tokens
        out_t = msg.usage.output_tokens
        return LLMResponse(
            text=text,
            usage=LLMUsage(in_t, out_t, _cost(self.model, in_t, out_t)),
            model=self.model,
            provider=self.provider,
            raw=msg,
        )
