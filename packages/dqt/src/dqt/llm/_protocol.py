"""Canonical LLM provider contract. One shape for every LLM call in the library."""
from __future__ import annotations

from typing import Protocol, TypedDict, runtime_checkable


class Message(TypedDict):
    role: str  # "user" | "assistant"
    content: str


@runtime_checkable
class LLMProvider(Protocol):
    """A minimal text-completion provider. Implementations wrap a single backend."""

    model: str

    def complete(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        """Return the assistant's text for a chat completion.

        `system` is the system prompt (kept separate so each backend can place it
        where it belongs). `model`/`max_tokens`/`temperature` override the
        provider defaults for this call only.
        """
        ...
