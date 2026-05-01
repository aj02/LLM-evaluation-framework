"""Build LLM clients by short name."""
from __future__ import annotations

from evalkit.llm.base import LLMClient


def build_client(spec: str) -> LLMClient:
    """Build a client from a `provider:model` string.

    Examples::

        build_client("anthropic:claude-sonnet-4-6")
        build_client("openai:gpt-4o-mini")
        build_client("anthropic")  # uses provider's default model
    """
    if ":" in spec:
        provider, model = spec.split(":", 1)
    else:
        provider, model = spec, ""

    provider = provider.strip().lower()
    model = model.strip()

    if provider == "anthropic":
        from evalkit.llm.anthropic import AnthropicClient
        return AnthropicClient(model=model or "claude-sonnet-4-6")
    if provider == "openai":
        from evalkit.llm.openai import OpenAIClient
        return OpenAIClient(model=model or "gpt-4o-mini")
    raise ValueError(f"unknown LLM provider: {provider!r} (expected 'anthropic' or 'openai')")
