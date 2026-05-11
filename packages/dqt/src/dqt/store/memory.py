from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from dqt.store._protocol import CausalEdgeReview, Incident, RunResult


class MemoryStore:
    def __init__(self) -> None:
        self._runs: dict[UUID, list[RunResult]] = defaultdict(list)
        self._incidents: dict[UUID, list[Incident]] = defaultdict(list)
        self._causal_reviews: list[CausalEdgeReview] = []

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

    def save_causal_review(self, review: CausalEdgeReview) -> None:
        self._causal_reviews.append(review)

    def list_causal_reviews(self, edge_id: UUID) -> list[CausalEdgeReview]:
        return [r for r in self._causal_reviews if r.edge_id == edge_id]

    def causal_edge_precision(self, edge_id: UUID) -> float:
        reviews = self.list_causal_reviews(edge_id)
        decided = [r for r in reviews if r.decision in ("accept", "reject")]
        if not decided:
            return float("nan")
        return sum(1 for r in decided if r.decision == "accept") / len(decided)
