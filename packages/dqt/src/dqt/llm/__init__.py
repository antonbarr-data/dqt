"""Canonical LLM entry point for the library.

Every LLM call goes through `get_llm()`, which returns a provider configured from
the environment, or `None` when unconfigured (so AI features degrade off cleanly).

Providers (`DQT_LLM_PROVIDER`):
- "anthropic" (default): direct Claude. Needs ANTHROPIC_API_KEY. Model: ANTHROPIC_MODEL.
- "litellm": OpenAI-compatible / proxy. Needs LITELLM_MODEL + (LITELLM_API_KEY or
  LITELLM_API_BASE, or a native provider key like OPENAI_API_KEY).

Shared knobs: DQT_LLM_MAX_TOKENS, DQT_LLM_TEMPERATURE, DQT_LLM_TIMEOUT_SECONDS.
"""
from __future__ import annotations

import os

from dqt.llm._protocol import LLMProvider, Message

__all__ = ["LLMProvider", "Message", "get_llm"]

_DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
# Native keys LiteLLM can pick up when calling providers directly (no proxy).
_LITELLM_NATIVE_KEYS = (
    "OPENAI_API_KEY", "AZURE_API_KEY", "GEMINI_API_KEY",
    "ANTHROPIC_API_KEY", "COHERE_API_KEY", "MISTRAL_API_KEY",
)


def get_llm(provider: str | None = None) -> LLMProvider | None:
    """Build the configured LLM provider, or None if the active one is unconfigured."""
    provider = (provider or os.environ.get("DQT_LLM_PROVIDER", "anthropic")).strip().lower()
    max_tokens = int(os.environ.get("DQT_LLM_MAX_TOKENS", "1024"))
    temperature = float(os.environ.get("DQT_LLM_TEMPERATURE", "0"))
    timeout = float(os.environ.get("DQT_LLM_TIMEOUT_SECONDS", "60"))

    if provider == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return None
        from dqt.llm.anthropic import AnthropicProvider

        return AnthropicProvider(
            api_key=api_key,
            model=os.environ.get("ANTHROPIC_MODEL", _DEFAULT_ANTHROPIC_MODEL),
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )

    if provider == "litellm":
        model = os.environ.get("LITELLM_MODEL", "")
        api_base = os.environ.get("LITELLM_API_BASE", "")
        api_key = os.environ.get("LITELLM_API_KEY", "")
        has_native = any(os.environ.get(k) for k in _LITELLM_NATIVE_KEYS)
        if not model or not (api_key or api_base or has_native):
            return None
        from dqt.llm.litellm import LiteLLMProvider

        return LiteLLMProvider(
            model=model,
            api_base=api_base or None,
            api_key=api_key or None,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )

    raise ValueError(
        f"Unknown DQT_LLM_PROVIDER: {provider!r} (expected 'anthropic' or 'litellm')"
    )
