# packages/dqt/src/dqt/store/postgres.py
"""PostgreSQL-backed ResultsStore. Requires psycopg2: pip install 'dqtlib[postgres]'."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from dqt.store._protocol import CausalEdgeReview, CausalityReport, Incident, ProfileReport, RunResult
from dqt.store.proof import ProofBundle
from dqt.algorithms._base import Verdict
from dqt.utils.logging import get_logger

_log = get_logger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS dqt_runs (
    run_id UUID PRIMARY KEY,
    check_id UUID NOT NULL,
    detector_slug TEXT NOT NULL,
    detector_version TEXT NOT NULL DEFAULT '1',
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ NOT NULL,
    verdict TEXT NOT NULL,
    score DOUBLE PRECISION NOT NULL,
    plain_english TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}',
    diagnostic_sql TEXT
);
CREATE INDEX IF NOT EXISTS idx_dqt_runs_check_id ON dqt_runs(check_id, finished_at DESC);

CREATE TABLE IF NOT EXISTS dqt_incidents (
    incident_id UUID PRIMARY KEY,
    check_id UUID NOT NULL,
    run_id UUID NOT NULL,
    detector_slug TEXT NOT NULL,
    severity TEXT NOT NULL,
    opened_at TIMESTAMPTZ NOT NULL,
    score DOUBLE PRECISION NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    resolved_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_dqt_incidents_check_id ON dqt_incidents(check_id);

CREATE TABLE IF NOT EXISTS dqt_proofs (
    commitment TEXT PRIMARY KEY,
    run_id UUID NOT NULL,
    check_id UUID NOT NULL,
    detector_slug TEXT NOT NULL,
    detector_version TEXT NOT NULL,
    data_hash TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    commitment_algorithm TEXT NOT NULL DEFAULT 'sha256',
    computed_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dqt_proofs_check_id ON dqt_proofs(check_id);

CREATE TABLE IF NOT EXISTS dqt_causal_reviews (
    review_id UUID PRIMARY KEY,
    edge_id UUID NOT NULL,
    cause TEXT NOT NULL,
    effect TEXT NOT NULL,
    decision TEXT NOT NULL,
    reviewer TEXT NOT NULL,
    reviewed_at TIMESTAMPTZ NOT NULL,
    reason TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_dqt_causal_reviews_edge_id ON dqt_causal_reviews(edge_id);
"""


class PostgresStore:
    """Persistent ResultsStore backed by PostgreSQL.

    Args:
        dsn: PostgreSQL connection string, e.g. 'postgresql://user:pass@host:5432/dbname'
    """

    def __init__(self, dsn: str) -> None:
        try:
            import psycopg2
            import psycopg2.extras
        except ImportError as exc:
            raise ImportError(
                "PostgresStore requires psycopg2. "
                "Install via: pip install 'dqtlib[postgres]'"
            ) from exc
        self._psycopg2 = psycopg2
        self._extras = psycopg2.extras
        self._dsn = dsn
        self._conn = psycopg2.connect(dsn)
        self._conn.autocommit = False
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._conn.cursor() as cur:
            cur.execute(_DDL)
        self._conn.commit()

    def _cursor(self):
        return self._conn.cursor(cursor_factory=self._extras.RealDictCursor)

    def save_run(self, run: RunResult) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO dqt_runs
                    (run_id, check_id, detector_slug, detector_version,
                     started_at, finished_at, verdict, score, plain_english,
                     details, diagnostic_sql)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (run_id) DO NOTHING
                """,
                (
                    str(run.run_id), str(run.check_id), run.detector_slug,
                    run.detector_version, run.started_at, run.finished_at,
                    run.verdict.value, run.score, run.plain_english,
                    json.dumps(run.details), run.diagnostic_sql,
                ),
            )
        self._conn.commit()

    def list_runs(self, check_id: UUID, limit: int = 100) -> list[RunResult]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM dqt_runs WHERE check_id=%s ORDER BY finished_at DESC LIMIT %s",
                (str(check_id), limit),
            )
            rows = cur.fetchall()
        return [self._row_to_run(r) for r in rows]

    def query_runs(
        self,
        check_id: UUID | None = None,
        verdict: Verdict | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> list[RunResult]:
        clauses = []
        params = []
        if check_id is not None:
            clauses.append("check_id = %s")
            params.append(str(check_id))
        if verdict is not None:
            clauses.append("verdict = %s")
            params.append(verdict.value)
        if since is not None:
            clauses.append("finished_at >= %s")
            params.append(since)
        if until is not None:
            clauses.append("finished_at <= %s")
            params.append(until)
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        params.append(limit)
        with self._cursor() as cur:
            cur.execute(
                f"SELECT * FROM dqt_runs {where} ORDER BY finished_at DESC LIMIT %s",
                params,
            )
            rows = cur.fetchall()
        return [self._row_to_run(r) for r in rows]

    @staticmethod
    def _row_to_run(r: dict) -> RunResult:
        return RunResult(
            run_id=UUID(r["run_id"]),
            check_id=UUID(r["check_id"]),
            detector_slug=r["detector_slug"],
            detector_version=r["detector_version"],
            started_at=r["started_at"],
            finished_at=r["finished_at"],
            verdict=Verdict(r["verdict"]),
            score=float(r["score"]),
            plain_english=r["plain_english"],
            details=r["details"] or {},
            diagnostic_sql=r["diagnostic_sql"],
        )

    def save_incident(self, incident: Incident) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO dqt_incidents
                    (incident_id, check_id, run_id, detector_slug, severity,
                     opened_at, score, status, resolved_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (incident_id) DO NOTHING
                """,
                (
                    str(incident.incident_id), str(incident.check_id),
                    str(incident.run_id), incident.detector_slug,
                    incident.severity.value, incident.opened_at,
                    incident.score, incident.status, incident.resolved_at,
                ),
            )
        self._conn.commit()

    def list_incidents(self, check_id: UUID, status: str | None = None) -> list[Incident]:
        with self._cursor() as cur:
            if status is not None:
                cur.execute(
                    "SELECT * FROM dqt_incidents WHERE check_id=%s AND status=%s ORDER BY opened_at DESC",
                    (str(check_id), status),
                )
            else:
                cur.execute(
                    "SELECT * FROM dqt_incidents WHERE check_id=%s ORDER BY opened_at DESC",
                    (str(check_id),),
                )
            rows = cur.fetchall()
        return [self._row_to_incident(r) for r in rows]

    def list_all_incidents(self) -> list[Incident]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM dqt_incidents ORDER BY opened_at DESC")
            rows = cur.fetchall()
        return [self._row_to_incident(r) for r in rows]

    @staticmethod
    def _row_to_incident(r: dict) -> Incident:
        return Incident(
            incident_id=UUID(r["incident_id"]),
            check_id=UUID(r["check_id"]),
            run_id=UUID(r["run_id"]),
            detector_slug=r["detector_slug"],
            severity=Verdict(r["severity"]),
            opened_at=r["opened_at"],
            score=float(r["score"]),
            status=r["status"],
            resolved_at=r.get("resolved_at"),
        )

    def save_proof(self, proof: ProofBundle) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO dqt_proofs
                    (commitment, run_id, check_id, detector_slug, detector_version,
                     data_hash, row_count, commitment_algorithm, computed_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (commitment) DO NOTHING
                """,
                (
                    proof.commitment, str(proof.run_id), str(proof.check_id),
                    proof.detector_slug, proof.detector_version, proof.data_hash,
                    proof.row_count, proof.commitment_algorithm, proof.computed_at,
                ),
            )
        self._conn.commit()

    def list_proofs(self, check_id: UUID) -> list[ProofBundle]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM dqt_proofs WHERE check_id=%s ORDER BY computed_at DESC",
                (str(check_id),),
            )
            rows = cur.fetchall()
        return [self._row_to_proof(r) for r in rows]

    @staticmethod
    def _row_to_proof(r: dict) -> ProofBundle:
        return ProofBundle(
            run_id=UUID(r["run_id"]),
            check_id=UUID(r["check_id"]),
            detector_slug=r["detector_slug"],
            detector_version=r["detector_version"],
            data_hash=r["data_hash"],
            row_count=int(r["row_count"]),
            commitment=r["commitment"],
            commitment_algorithm=r["commitment_algorithm"],
            computed_at=r["computed_at"],
        )

    def save_causal_review(self, review: CausalEdgeReview) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO dqt_causal_reviews
                    (review_id, edge_id, cause, effect, decision, reviewer, reviewed_at, reason)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (review_id) DO NOTHING
                """,
                (
                    str(review.review_id), str(review.edge_id), review.cause,
                    review.effect, review.decision, review.reviewer,
                    review.reviewed_at, review.reason,
                ),
            )
        self._conn.commit()

    def list_causal_reviews(self, edge_id: UUID) -> list[CausalEdgeReview]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM dqt_causal_reviews WHERE edge_id=%s ORDER BY reviewed_at DESC",
                (str(edge_id),),
            )
            rows = cur.fetchall()
        return [self._row_to_review(r) for r in rows]

    @staticmethod
    def _row_to_review(r: dict) -> CausalEdgeReview:
        return CausalEdgeReview(
            review_id=UUID(r["review_id"]),
            edge_id=UUID(r["edge_id"]),
            cause=r["cause"],
            effect=r["effect"],
            decision=r["decision"],
            reviewer=r["reviewer"],
            reviewed_at=r["reviewed_at"],
            reason=r["reason"],
        )

    def causal_edge_precision(self, edge_id: UUID) -> float:
        reviews = self.list_causal_reviews(edge_id)
        decided = [r for r in reviews if r.decision in ("accept", "reject")]
        if not decided:
            return float("nan")
        return sum(1 for r in decided if r.decision == "accept") / len(decided)

    def save_profile_report(self, report: ProfileReport) -> None:
        _log.warning("postgres_store_profile_report_in_memory", report_id=str(report.report_id))

    def list_profile_reports(self) -> list[ProfileReport]:
        return []

    def save_causality_report(self, report: CausalityReport) -> None:
        _log.warning("postgres_store_causality_report_in_memory", report_id=str(report.report_id))

    def list_causality_reports(self) -> list[CausalityReport]:
        return []

    def close(self) -> None:
        self._conn.close()
