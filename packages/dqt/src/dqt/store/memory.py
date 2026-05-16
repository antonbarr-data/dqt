from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from uuid import UUID

from dqt.store._protocol import CausalEdgeReview, CausalityReport, Incident, MetricRun, ProfileReport, RunResult

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dqt.algorithms._base import Verdict
    from dqt.store.proof import ProofBundle


class MemoryStore:
    def __init__(self) -> None:
        self._runs: dict[UUID, list[RunResult]] = defaultdict(list)
        self._incidents: dict[UUID, list[Incident]] = defaultdict(list)
        self._causal_reviews: list[CausalEdgeReview] = []
        self._profile_reports: list[ProfileReport] = []
        self._causality_reports: list[CausalityReport] = []
        self._proofs: dict[UUID, list[ProofBundle]] = defaultdict(list)
        self._metric_runs: dict[str, list[MetricRun]] = {}

    def save_run(self, run: RunResult) -> None:
        self._runs[run.check_id].append(run)

    def list_runs(self, check_id: UUID, limit: int = 100) -> list[RunResult]:
        return self._runs[check_id][-limit:][::-1]

    def query_runs(
        self,
        check_id: UUID | None = None,
        verdict: Verdict | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> list[RunResult]:
        if check_id is not None:
            candidates = list(self._runs.get(check_id, []))
        else:
            candidates = [r for runs in self._runs.values() for r in runs]
        if verdict is not None:
            candidates = [r for r in candidates if r.verdict == verdict]
        if since is not None:
            candidates = [r for r in candidates if r.finished_at >= since]
        if until is not None:
            candidates = [r for r in candidates if r.finished_at <= until]
        candidates.sort(key=lambda r: r.finished_at, reverse=True)
        return candidates[:limit]

    def save_incident(self, incident: Incident) -> None:
        self._incidents[incident.check_id].append(incident)

    def list_incidents(self, check_id: UUID, status: str | None = None) -> list[Incident]:
        items = self._incidents[check_id]
        if status is not None:
            items = [i for i in items if i.status == status]
        return list(items)

    def list_all_incidents(self) -> list[Incident]:
        result = []
        for inc_list in self._incidents.values():
            result.extend(inc_list)
        return result

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

    def save_profile_report(self, report: ProfileReport) -> None:
        self._profile_reports.append(report)

    def list_profile_reports(self) -> list[ProfileReport]:
        return list(self._profile_reports)

    def save_causality_report(self, report: CausalityReport) -> None:
        self._causality_reports.append(report)

    def list_causality_reports(self) -> list[CausalityReport]:
        return list(self._causality_reports)

    def save_proof(self, proof: ProofBundle) -> None:
        self._proofs[proof.check_id].append(proof)

    def list_proofs(self, check_id: UUID) -> list[ProofBundle]:
        return list(self._proofs.get(check_id, []))

    def list_check_ids(self) -> list[UUID]:
        return list(self._runs.keys())

    def save_metric_run(self, run: MetricRun) -> None:
        self._metric_runs.setdefault(run.metric_fqn, []).append(run)

    def list_metric_runs(self, metric_fqn: str, lookback_days: int = 30) -> list[MetricRun]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        runs = self._metric_runs.get(metric_fqn, [])
        return sorted(
            [r for r in runs if r.run_at >= cutoff],
            key=lambda r: r.run_at,
        )
