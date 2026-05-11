from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable
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

    def to_bundle(self, path: str | Path) -> None:
        """Write reproducibility artifacts to a directory.

        Creates:
          result.json      — score, verdict, plain_english, details
          config.json      — check configuration from ReproducibilityBundle
          environment.json — dqt version, Python version, platform
          diagnostic.sql   — failing-rows query (if available)
        """
        import json
        import platform
        import sys

        out = Path(path)
        out.mkdir(parents=True, exist_ok=True)

        (out / "result.json").write_text(json.dumps({
            "check_id": str(self.check_id),
            "run_id": str(self.run_id),
            "detector_slug": self.detector_slug,
            "verdict": self.verdict.value,
            "score": self.score,
            "plain_english": self.plain_english,
            "details": self.details,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
        }, indent=2))

        bundle = self.reproducibility
        config: dict = {"detector_slug": self.detector_slug}
        if bundle:
            config.update({
                "detector_params": bundle.detector_params,
                "schema_name": bundle.schema_name,
                "table_name": bundle.table_name,
                "column_name": bundle.column_name,
                "sample_n": bundle.sample_n,
                "detector_state": bundle.detector_state_json,
                "notes": bundle.notes,
            })
        (out / "config.json").write_text(json.dumps(config, indent=2))

        try:
            from dqt import __version__ as dqt_version
        except Exception:
            dqt_version = "unknown"
        (out / "environment.json").write_text(json.dumps({
            "dqt_version": dqt_version,
            "python_version": sys.version,
            "platform": platform.platform(),
        }, indent=2))

        if self.diagnostic_sql:
            (out / "diagnostic.sql").write_text(self.diagnostic_sql)


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


@dataclass
class CausalEdgeReview:
    """Human review decision for a proposed causal edge."""
    edge_id: UUID
    cause: str
    effect: str
    decision: Literal["accept", "reject", "defer"]
    reviewer: str
    reviewed_at: datetime
    reason: str = ""
    review_id: UUID = field(default_factory=uuid4)


@runtime_checkable
class ResultsStore(Protocol):
    def save_run(self, run: RunResult) -> None: ...
    def list_runs(self, check_id: UUID, limit: int = 100) -> list[RunResult]: ...
    def save_incident(self, incident: Incident) -> None: ...
    def list_incidents(self, check_id: UUID, status: str | None = None) -> list[Incident]: ...
    def save_causal_review(self, review: CausalEdgeReview) -> None: ...
    def list_causal_reviews(self, edge_id: UUID) -> list[CausalEdgeReview]: ...
    def causal_edge_precision(self, edge_id: UUID) -> float: ...
