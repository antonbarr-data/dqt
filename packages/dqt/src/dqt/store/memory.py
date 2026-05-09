from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from dqt.store._protocol import Incident, RunResult


class MemoryStore:
    def __init__(self) -> None:
        self._runs: dict[UUID, list[RunResult]] = defaultdict(list)
        self._incidents: dict[UUID, list[Incident]] = defaultdict(list)

    def save_run(self, run: RunResult) -> None:
        self._runs[run.check_id].append(run)

    def list_runs(self, check_id: UUID, limit: int = 100) -> list[RunResult]:
        return self._runs[check_id][-limit:][::-1]

    def save_incident(self, incident: Incident) -> None:
        self._incidents[incident.check_id].append(incident)

    def list_incidents(self, check_id: UUID, status: str | None = None) -> list[Incident]:
        items = self._incidents[check_id]
        if status is not None:
            items = [i for i in items if i.status == status]
        return list(items)
