"""OpenAI implementation."""
from __future__ import annotations

import os

from evalkit.llm.base import LLMClient, LLMResponse, LLMUsage

_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
    "o3-mini": (1.10, 4.40),
}


def _cost(model: str, in_t: int, out_t: int) -> float:
    if model not in _PRICING:
        return 0.0
    in_per_m, out_per_m = _PRICING[model]
    return (in_t / 1_000_000) * in_per_m + (out_t / 1_000_000) * out_per_m


class OpenAIClient(LLMClient):
    provider = "openai"

    def __init__(
        self,
        *,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError("openai package is required") from e
        self.model = model
        self._client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> LLMResponse:
        resp = self._client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
        )
        text = resp.choices[0].message.content or ""
        usage = resp.usage
        in_t = usage.prompt_tokens if usage else 0
        out_t = usage.completion_tokens if usage else 0
        return LLMResponse(
            text=text,
            usage=LLMUsage(in_t, out_t, _cost(self.model, in_t, out_t)),
            model=self.model,
            provider=self.provider,
            raw=resp,
        )
