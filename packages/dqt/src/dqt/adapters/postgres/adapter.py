# PostgresAdapter wraps SQLAlchemy for all warehouse operations.
# Sampling uses LIMIT for portable random rows; TABLESAMPLE BERNOULLI available as an option.
from __future__ import annotations

import datetime
import time
from typing import Any

import pandas as pd
import sqlalchemy as sa

from dqt.adapters._protocol import (
    AggExpr,
    ColumnMeta,
    HealthCheckResult,
    HealthCheckStep,
)
from dqt.utils.logging import get_logger

_log = get_logger(__name__)


class PostgresAdapter:
    def __init__(self, conn_str: str) -> None:
        self._conn_str = conn_str
        self._engine = sa.create_engine(conn_str, pool_pre_ping=True)

    def health_check(self) -> HealthCheckResult:
        steps: list[HealthCheckStep] = []
        steps.append(self._step_tcp())
        if steps[-1].status == "fail":
            for name in ("auth", "info_schema", "sample_select", "latency_probe", "clock_skew"):
                steps.append(HealthCheckStep(name=name, status="skip", latency_ms=0.0, detail="skipped"))
            return HealthCheckResult(steps=steps)
        steps.append(self._step_auth())
        steps.append(self._step_info_schema())
        steps.append(self._step_sample_select())
        steps.append(self._step_latency())
        steps.append(self._step_clock_skew())
        return HealthCheckResult(steps=steps)

    def _step_tcp(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            with self._engine.connect() as conn:
                conn.execute(sa.text("SELECT 1"))
            return HealthCheckStep("tcp_reach", "pass", (time.perf_counter() - t0) * 1000, "ok")
        except Exception as exc:
            return HealthCheckStep("tcp_reach", "fail", 0.0, str(exc))

    def _step_auth(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            with self._engine.connect() as conn:
                user = conn.execute(sa.text("SELECT current_user")).scalar()
            return HealthCheckStep("auth", "pass", (time.perf_counter() - t0) * 1000, f"user={user}")
        except Exception as exc:
            return HealthCheckStep("auth", "fail", 0.0, str(exc))

    def _step_info_schema(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            with self._engine.connect() as conn:
                conn.execute(sa.text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema NOT IN ('pg_catalog','information_schema')"
                )).scalar()
            return HealthCheckStep("info_schema", "pass", (time.perf_counter() - t0) * 1000, "readable")
        except Exception as exc:
            return HealthCheckStep("info_schema", "fail", 0.0, str(exc))

    def _step_sample_select(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            with self._engine.connect() as conn:
                conn.execute(sa.text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema NOT IN ('pg_catalog','information_schema') LIMIT 1"
                )).fetchone()
            return HealthCheckStep("sample_select", "pass", (time.perf_counter() - t0) * 1000, "ok")
        except Exception as exc:
            return HealthCheckStep("sample_select", "fail", 0.0, str(exc))

    def _step_latency(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            with self._engine.connect() as conn:
                conn.execute(sa.text("SELECT 1"))
            latency = (time.perf_counter() - t0) * 1000
            return HealthCheckStep("latency_probe", "pass", latency, f"{latency:.1f}ms")
        except Exception as exc:
            return HealthCheckStep("latency_probe", "fail", 0.0, str(exc))

    def _step_clock_skew(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            with self._engine.connect() as conn:
                db_now = conn.execute(sa.text("SELECT NOW()")).scalar()
            local_now = datetime.datetime.now(datetime.timezone.utc)
            if db_now.tzinfo is None:
                db_now = db_now.replace(tzinfo=datetime.timezone.utc)
            skew_s = abs((db_now - local_now).total_seconds())
            status = "pass" if skew_s < 60 else "fail"
            return HealthCheckStep("clock_skew", status, (time.perf_counter() - t0) * 1000, f"skew={skew_s:.1f}s")
        except Exception as exc:
            return HealthCheckStep("clock_skew", "fail", 0.0, str(exc))

    def list_schemas(self) -> list[str]:
        with self._engine.connect() as conn:
            rows = conn.execute(sa.text(
                "SELECT DISTINCT table_schema FROM information_schema.tables "
                "WHERE table_schema NOT IN ('pg_catalog','information_schema') ORDER BY 1"
            )).fetchall()
        return [r[0] for r in rows]

    def list_tables(self, schema: str) -> list[str]:
        with self._engine.connect() as conn:
            rows = conn.execute(sa.text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = :schema ORDER BY 1"
            ), {"schema": schema}).fetchall()
        return [r[0] for r in rows]

    def describe_columns(self, schema: str, table: str) -> list[ColumnMeta]:
        with self._engine.connect() as conn:
            rows = conn.execute(sa.text(
                "SELECT column_name, data_type, is_nullable, ordinal_position "
                "FROM information_schema.columns "
                "WHERE table_schema = :schema AND table_name = :table "
                "ORDER BY ordinal_position"
            ), {"schema": schema, "table": table}).fetchall()
        return [
            ColumnMeta(name=r[0], data_type=r[1], nullable=(r[2] == "YES"), position=r[3])
            for r in rows
        ]

    def sample(self, schema: str, table: str, n: int = 100_000) -> pd.DataFrame:
        # Use ORDER BY random() to get a genuine random sample without TABLESAMPLE bias on small tables.
        query = sa.text(f'SELECT * FROM "{schema}"."{table}" ORDER BY random() LIMIT :n')  # noqa: S608
        with self._engine.connect() as conn:
            return pd.read_sql(query, conn, params={"n": n})

    def aggregate(self, schema: str, table: str, exprs: list[AggExpr]) -> dict[str, Any]:
        cols = ", ".join(f"{e.sql} AS {e.name}" for e in exprs)
        query = sa.text(f'SELECT {cols} FROM "{schema}"."{table}"')  # noqa: S608
        with self._engine.connect() as conn:
            row = conn.execute(query).fetchone()
        return dict(zip([e.name for e in exprs], row))
