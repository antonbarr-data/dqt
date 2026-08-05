"""LiteLLM backend (OpenAI-compatible). Requires the `litellm` package (dqt[llm]).

Works against a LiteLLM proxy (set api_base + a virtual key) or calls providers
directly (LiteLLM reads native keys like OPENAI_API_KEY from the environment).
"""
from __future__ import annotations

from dqt.llm._protocol import Message


class LiteLLMProvider:
    def __init__(
        self,
        *,
        model: str,
        api_base: str | None = None,
        api_key: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        timeout: float = 60.0,
    ) -> None:
        self.model = model
        self.api_base = api_base
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout

    def complete(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        import litellm

        full: list[Message] = []
        if system:
            full.append({"role": "system", "content": system})
        full.extend(messages)
        kwargs: dict = {
            "model": model or self.model,
            "messages": full,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": self.temperature if temperature is None else temperature,
            "api_base": self.api_base or None,
            "api_key": self.api_key or None,
            "timeout": self.timeout,
        }
        # A configured api_base means an OpenAI-compatible LiteLLM proxy: route to it
        # and forward the model name as registered, instead of provider auto-routing.
        if self.api_base:
            kwargs["custom_llm_provider"] = "litellm_proxy"
        resp = litellm.completion(**kwargs)
        return resp.choices[0].message.content.strip()
