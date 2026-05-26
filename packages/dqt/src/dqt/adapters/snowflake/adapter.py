# SnowflakeAdapter uses snowflake-connector-python (official Snowflake client).
# Each public method opens a fresh connection — Snowflake tokens persist across calls
# so reconnect overhead is minimal after the first login.
from __future__ import annotations

import contextlib
import datetime
import time
from typing import Any

import pandas as pd

from dqt.adapters._protocol import (
    AggExpr,
    ColumnMeta,
    HealthCheckResult,
    HealthCheckStep,
)
from dqt.utils.logging import get_logger

_log = get_logger(__name__)

# Schemas that Snowflake creates automatically — excluded from user-visible list.
_SYSTEM_SCHEMAS = frozenset({"INFORMATION_SCHEMA"})


class SnowflakeAdapter:
    sql_dialect = "snowflake"

    def __init__(self, **conn_kwargs: Any) -> None:
        try:
            import snowflake.connector  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "snowflake-connector-python is required for SnowflakeAdapter. "
                "Install with: pip install snowflake-connector-python"
            ) from exc
        self._conn_kwargs = conn_kwargs

    @contextlib.contextmanager
    def _connect(self):
        import snowflake.connector
        conn = snowflake.connector.connect(**self._conn_kwargs)
        try:
            yield conn
        finally:
            conn.close()

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
        steps.append(HealthCheckStep("clock_skew", "skip", 0.0, "managed service"))
        return HealthCheckResult(steps=steps)

    def _step_tcp(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            with self._connect() as conn:
                conn.cursor().execute("SELECT 1")
            return HealthCheckStep("tcp_reach", "pass", (time.perf_counter() - t0) * 1000, "ok")
        except Exception as exc:
            return HealthCheckStep("tcp_reach", "fail", 0.0, str(exc))

    def _step_auth(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            with self._connect() as conn:
                cur = conn.cursor()
                cur.execute("SELECT CURRENT_USER()")
                user = cur.fetchone()[0]
            return HealthCheckStep("auth", "pass", (time.perf_counter() - t0) * 1000, f"user={user}")
        except Exception as exc:
            return HealthCheckStep("auth", "fail", 0.0, str(exc))

    def _step_info_schema(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            with self._connect() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema NOT IN ('INFORMATION_SCHEMA')"
                )
                cur.fetchone()
            return HealthCheckStep("info_schema", "pass", (time.perf_counter() - t0) * 1000, "readable")
        except Exception as exc:
            return HealthCheckStep("info_schema", "fail", 0.0, str(exc))

    def _step_sample_select(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            with self._connect() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema NOT IN ('INFORMATION_SCHEMA') LIMIT 1"
                )
                cur.fetchone()
            return HealthCheckStep("sample_select", "pass", (time.perf_counter() - t0) * 1000, "ok")
        except Exception as exc:
            return HealthCheckStep("sample_select", "fail", 0.0, str(exc))

    def _step_latency(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            with self._connect() as conn:
                conn.cursor().execute("SELECT 1")
            latency = (time.perf_counter() - t0) * 1000
            return HealthCheckStep("latency_probe", "pass", latency, f"{latency:.1f}ms")
        except Exception as exc:
            return HealthCheckStep("latency_probe", "fail", 0.0, str(exc))

    def list_schemas(self) -> list[str]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT schema_name FROM information_schema.schemata "
                "WHERE schema_name NOT IN ('INFORMATION_SCHEMA') ORDER BY 1"
            )
            return [row[0] for row in cur.fetchall()]

    def list_tables(self, schema: str) -> list[str]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = %s ORDER BY 1",
                (schema.upper(),),
            )
            return [row[0] for row in cur.fetchall()]

    def describe_columns(self, schema: str, table: str) -> list[ColumnMeta]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT column_name, data_type, is_nullable, ordinal_position "
                "FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = %s "
                "ORDER BY ordinal_position",
                (schema.upper(), table.upper()),
            )
            return [
                ColumnMeta(name=row[0], data_type=row[1], nullable=(row[2] == "YES"), position=row[3])
                for row in cur.fetchall()
            ]

    def sample(self, schema: str, table: str, n: int = 100_000, where: str | None = None) -> pd.DataFrame:
        with self._connect() as conn:
            cur = conn.cursor()
            if where:
                # SAMPLE can't be combined with WHERE; fall back to ORDER BY RANDOM() LIMIT.
                cur.execute(f'SELECT * FROM "{schema}"."{table}" WHERE {where} ORDER BY RANDOM() LIMIT {n}')
            else:
                # SAMPLE ({n} ROWS) is Snowflake's efficient reservoir-sampler — uses block-level sampling.
                cur.execute(f'SELECT * FROM "{schema}"."{table}" SAMPLE ({n} ROWS)')
            cols = [desc[0] for desc in cur.description]
            return pd.DataFrame(cur.fetchall(), columns=cols)

    def aggregate(self, schema: str, table: str, exprs: list[AggExpr]) -> dict[str, Any]:
        cols = ", ".join(f"{e.sql} AS {e.name}" for e in exprs)
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(f'SELECT {cols} FROM "{schema}"."{table}"')
            row = cur.fetchone()
        return dict(zip([e.name for e in exprs], row or [None] * len(exprs)))
