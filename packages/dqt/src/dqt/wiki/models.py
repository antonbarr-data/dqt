"""Data models for the dqt LLM Wiki pipeline."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RawDocument(BaseModel):
    """A single atomic source document loaded from raw/."""

    path: str  # relative to raw_dir
    kind: Literal["semantic", "ticket", "code", "report", "other"]
    content: str
    sha256: str


class WikiEntry(BaseModel):
    """A synthesised knowledge article written to wiki/."""

    id: str
    title: str
    kind: str
    body: str  # full synthesised markdown
    source_paths: list[str]
    content_hash: str  # sha256 of joined source content, used for cache invalidation
    generated_at: str  # ISO 8601


class SyncManifest(BaseModel):
    """Tracks which raw documents have been processed, keyed by entry id."""

    vault_dir: str
    raw_dir: str
    # entry_id -> content_hash that was used to generate it
    entries: dict[str, str] = Field(default_factory=dict)
    last_sync: str | None = None
