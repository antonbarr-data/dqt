from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable
from uuid import UUID, uuid4

from dqt.algorithms._base import Verdict


@dataclass
class ReproducibilityBundle:
    """Everything needed to reproduce a run result offline or in a different environment."""
    check_id: UUID
    run_id: UUID
    detector_slug: str
    detector_params: dict[str, Any]
    schema_name: str
    table_name: str
    column_name: str | None
    sample_n: int
    # Serialised detector state (fit output) — JSON-serialisable dict
    detector_state_json: dict[str, Any] = field(default_factory=dict)
    # Reproducibility notes (e.g. "state contains sklearn model — re-fit required")
    notes: str = ""


@dataclass
class RunResult:
    check_id: UUID
    detector_slug: str
    started_at: datetime
    finished_at: datetime
    verdict: Verdict
    score: float
    plain_english: str
    details: dict[str, Any] = field(default_factory=dict)
    run_id: UUID = field(default_factory=uuid4)
    # SQL the on-call team can run to inspect failing rows directly in the warehouse
    diagnostic_sql: str | None = None
    # Bundle for offline reproduction / audit
    reproducibility: ReproducibilityBundle | None = None


@dataclass
class Incident:
    check_id: UUID
    run_id: UUID
    detector_slug: str
    # temporary: Verdict used as severity stand-in until severity.config.json enum is generated
    severity: Verdict
    opened_at: datetime
    score: float
    incident_id: UUID = field(default_factory=uuid4)
    status: str = "open"
    resolved_at: datetime | None = None


@runtime_checkable
class ResultsStore(Protocol):
    def save_run(self, run: RunResult) -> None: ...
    def list_runs(self, check_id: UUID, limit: int = 100) -> list[RunResult]: ...
    def save_incident(self, incident: Incident) -> None: ...
    def list_incidents(self, check_id: UUID, status: str | None = None) -> list[Incident]: ...
