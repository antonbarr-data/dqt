"""Models for Google OKF / Apache Ossie repo ingestion.

A KnowledgeRepo binds a Git repo to an existing Source. Ingesting it produces an
ImportProposal (the extracted, reviewable candidate tree, stored as JSONB) that the
user selects from before anything is written. Prose concepts land in KnowledgeArtifact,
the server-side agent knowledge store.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from dqt_server.db.engine import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeRepo(Base):
    __tablename__ = "knowledge_repos"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source_id: Mapped[str] = mapped_column(String, ForeignKey("sources.id"), nullable=False)
    git_url: Mapped[str] = mapped_column(String, nullable=False)
    branch: Mapped[str | None] = mapped_column(String, nullable=True)
    subpath: Mapped[str | None] = mapped_column(String, nullable=True)
    last_commit: Mapped[str | None] = mapped_column(String, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="registered")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class ImportProposal(Base):
    __tablename__ = "import_proposals"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    repo_id: Mapped[str] = mapped_column(String, ForeignKey("knowledge_repos.id"), nullable=False)
    source_id: Mapped[str] = mapped_column(String, ForeignKey("sources.id"), nullable=False)
    # pending -> ready | failed ; applied set separately via applied_at
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    commit: Mapped[str | None] = mapped_column(String, nullable=True)
    # Full reviewable tree: {datasets:[...], knowledge:[...], checks:[...], conflicts, sources_seen}
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KnowledgeArtifact(Base):
    """Prose concept (playbook / runbook / policy) for the agent knowledge store."""
    __tablename__ = "knowledge_artifacts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source_id: Mapped[str] = mapped_column(String, ForeignKey("sources.id"), nullable=False)
    repo_id: Mapped[str | None] = mapped_column(String, ForeignKey("knowledge_repos.id"), nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False, default="other")
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    provenance: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
