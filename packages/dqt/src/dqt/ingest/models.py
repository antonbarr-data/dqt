"""Canonical in-memory shape produced by ingesting Google OKF / Apache Ossie repos.

An `IngestProposal` is what the LLM extractor emits and what the review UI renders:
candidate datasets/columns/metrics (from the semantic repo) plus a prose knowledge
lane. It is provider- and warehouse-agnostic; the server later intersects it with a
live Source and maps it onto the existing dqt/v1 apply endpoints.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Format = Literal["okf", "ossie"]
MetricKind = Literal["sum", "count", "ratio", "model"]


class Provenance(BaseModel):
    format: Format
    path: str  # repo-relative file the concept came from


class ProposedColumn(BaseModel):
    name: str
    data_type: str | None = None
    nullable: bool | None = None
    description: str | None = None
    is_time: bool = False
    is_metric: bool = False
    primary_key: bool = False
    unique: bool = False


class ProposedMetric(BaseModel):
    name: str
    expression: str | None = None
    kind: MetricKind = "ratio"
    datatype: str | None = None
    description: str | None = None
    column_name: str | None = None  # None => table-level metric


class ProposedDataset(BaseModel):
    schema_name: str
    table: str
    description: str | None = None
    primary_key: list[str] = Field(default_factory=list)
    unique_keys: list[list[str]] = Field(default_factory=list)
    columns: list[ProposedColumn] = Field(default_factory=list)
    metrics: list[ProposedMetric] = Field(default_factory=list)
    provenance: list[Provenance] = Field(default_factory=list)

    @property
    def identity(self) -> str:
        return f"{self.schema_name}.{self.table}".lower()


class KnowledgeConcept(BaseModel):
    """Prose concept (playbook / runbook / policy) for the agent knowledge store."""
    title: str
    kind: str = "other"
    body: str
    provenance: Provenance | None = None


class UnitExtract(BaseModel):
    """The LLM's per-file output (before provenance + merge)."""
    datasets: list[ProposedDataset] = Field(default_factory=list)
    knowledge: list[KnowledgeConcept] = Field(default_factory=list)


class IngestProposal(BaseModel):
    datasets: list[ProposedDataset] = Field(default_factory=list)
    knowledge: list[KnowledgeConcept] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    sources_seen: list[str] = Field(default_factory=list)  # repo-relative paths ingested
