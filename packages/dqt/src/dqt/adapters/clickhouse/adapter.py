# ClickHouseAdapter uses clickhouse-connect (HTTP transport, official ClickHouse client).
from __future__ import annotations

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

# System databases excluded from user-visible schema list.
_SYSTEM_DBS = frozenset({"system", "information_schema", "INFORMATION_SCHEMA"})


class ClickHouseAdapter:
    def __init__(self, **client_kwargs: Any) -> None:
        try:
            import clickhouse_connect
        except ImportError as exc:
            raise ImportError(
                "clickhouse-connect is required for ClickHouseAdapter. "
                "Install with: pip install clickhouse-connect"
            ) from exc
        self._client = clickhouse_connect.get_client(**client_kwargs)

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
            self._client.command("SELECT 1")
            return HealthCheckStep("tcp_reach", "pass", (time.perf_counter() - t0) * 1000, "ok")
        except Exception as exc:
            return HealthCheckStep("tcp_reach", "fail", 0.0, str(exc))

    def _step_auth(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            user = self._client.command("SELECT currentUser()")
            return HealthCheckStep("auth", "pass", (time.perf_counter() - t0) * 1000, f"user={user}")
        except Exception as exc:
            return HealthCheckStep("auth", "fail", 0.0, str(exc))

    def _step_info_schema(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            self._client.command(
                "SELECT COUNT(*) FROM system.tables "
                "WHERE database NOT IN ('system','information_schema','INFORMATION_SCHEMA')"
            )
            return HealthCheckStep("info_schema", "pass", (time.perf_counter() - t0) * 1000, "readable")
        except Exception as exc:
            return HealthCheckStep("info_schema", "fail", 0.0, str(exc))

    def _step_sample_select(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            self._client.command(
                "SELECT name FROM system.tables "
                "WHERE database NOT IN ('system','information_schema','INFORMATION_SCHEMA') LIMIT 1"
            )
            return HealthCheckStep("sample_select", "pass", (time.perf_counter() - t0) * 1000, "ok")
        except Exception as exc:
            return HealthCheckStep("sample_select", "fail", 0.0, str(exc))

    def _step_latency(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            self._client.command("SELECT 1")
            latency = (time.perf_counter() - t0) * 1000
            return HealthCheckStep("latency_probe", "pass", latency, f"{latency:.1f}ms")
        except Exception as exc:
            return HealthCheckStep("latency_probe", "fail", 0.0, str(exc))

    def _step_clock_skew(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            db_now_str = self._client.command("SELECT now()")
            # clickhouse-connect may return a datetime object or a string depending on version
            if isinstance(db_now_str, datetime.datetime):
                db_now = db_now_str
            else:
                db_now = datetime.datetime.fromisoformat(str(db_now_str))
            local_now = datetime.datetime.now(datetime.timezone.utc)
            if db_now.tzinfo is None:
                db_now = db_now.replace(tzinfo=datetime.timezone.utc)
            skew_s = abs((db_now - local_now).total_seconds())
            status = "pass" if skew_s < 60 else "fail"
            return HealthCheckStep("clock_skew", status, (time.perf_counter() - t0) * 1000, f"skew={skew_s:.1f}s")
        except Exception as exc:
            return HealthCheckStep("clock_skew", "fail", 0.0, str(exc))

    def list_schemas(self) -> list[str]:
        result = self._client.query(
            "SELECT DISTINCT database FROM system.tables "
            "WHERE database NOT IN ('system','information_schema','INFORMATION_SCHEMA') "
            "ORDER BY database"
        )
        return [row[0] for row in result.result_rows]

    def list_tables(self, schema: str) -> list[str]:
        result = self._client.query(
            "SELECT name FROM system.tables WHERE database = {schema:String} ORDER BY name",
            parameters={"schema": schema},
        )
        return [row[0] for row in result.result_rows]

    def describe_columns(self, schema: str, table: str) -> list[ColumnMeta]:
        result = self._client.query(
            "SELECT name, type, 1 AS nullable, position "
            "FROM system.columns "
            "WHERE database = {schema:String} AND table = {table:String} "
            "ORDER BY position",
            parameters={"schema": schema, "table": table},
        )
        return [
            ColumnMeta(name=row[0], data_type=row[1], nullable=True, position=row[3])
            for row in result.result_rows
        ]

    def sample(self, schema: str, table: str, n: int = 100_000) -> pd.DataFrame:
        # ClickHouse rand() is fast — ORDER BY rand() on large tables can be expensive.
        # For production use, SAMPLE clause is preferable, but requires MergeTree engine.
        # We use ORDER BY rand() LIMIT n for correctness across all table engines.
        result = self._client.query(
            f"SELECT * FROM `{schema}`.`{table}` ORDER BY rand() LIMIT {n}"
        )
        return pd.DataFrame(result.result_rows, columns=result.column_names)

    def aggregate(self, schema: str, table: str, exprs: list[AggExpr]) -> dict[str, Any]:
        cols = ", ".join(f"{e.sql} AS {e.name}" for e in exprs)
        result = self._client.query(f"SELECT {cols} FROM `{schema}`.`{table}`")
        row = result.result_rows[0] if result.result_rows else [None] * len(exprs)
        return dict(zip([e.name for e in exprs], row))
