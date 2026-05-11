# DatabricksAdapter uses databricks-sql-connector (official Databricks SQL connector).
# Supports both Unity Catalog (three-level namespace) and legacy hive_metastore.
# TABLESAMPLE (n ROWS) is used for sampling — Databricks pushes this to Delta scan
# which is far cheaper than ORDER BY RAND() on large tables.
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


class DatabricksAdapter:
    def __init__(
        self,
        server_hostname: str,
        http_path: str,
        access_token: str,
        catalog: str = "hive_metastore",
        schema: str = "default",
    ) -> None:
        try:
            from databricks import sql as dbsql  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "databricks-sql-connector is required for DatabricksAdapter. "
                "Install with: pip install databricks-sql-connector"
            ) from exc
        self._server_hostname = server_hostname
        self._http_path = http_path
        self._access_token = access_token
        self._catalog = catalog
        self._default_schema = schema

    @contextlib.contextmanager
    def _connect(self):
        from databricks import sql as dbsql
        conn = dbsql.connect(
            server_hostname=self._server_hostname,
            http_path=self._http_path,
            access_token=self._access_token,
            catalog=self._catalog,
            schema=self._default_schema,
        )
        try:
            yield conn
        finally:
            conn.close()

    def _exec(self, conn, sql: str, fetch_all: bool = True):
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall() if fetch_all else cur.fetchone()

    def _exec_df(self, conn, sql: str) -> pd.DataFrame:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description] if cur.description else []
            return pd.DataFrame(rows, columns=cols)

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
            with self._connect() as conn:
                self._exec(conn, "SELECT 1", fetch_all=False)
            return HealthCheckStep("tcp_reach", "pass", (time.perf_counter() - t0) * 1000, "ok")
        except Exception as exc:
            return HealthCheckStep("tcp_reach", "fail", 0.0, str(exc))

    def _step_auth(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            with self._connect() as conn:
                row = self._exec(conn, "SELECT current_user()", fetch_all=False)
            user = row[0] if row else "unknown"
            return HealthCheckStep("auth", "pass", (time.perf_counter() - t0) * 1000, f"user={user}")
        except Exception as exc:
            return HealthCheckStep("auth", "fail", 0.0, str(exc))

    def _step_info_schema(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            with self._connect() as conn:
                rows = self._exec(conn, "SHOW SCHEMAS")
            return HealthCheckStep(
                "info_schema", "pass",
                (time.perf_counter() - t0) * 1000,
                f"{len(rows)} schemas",
            )
        except Exception as exc:
            return HealthCheckStep("info_schema", "fail", 0.0, str(exc))

    def _step_sample_select(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            with self._connect() as conn:
                self._exec(conn, "SHOW TABLES LIMIT 1", fetch_all=False)
            return HealthCheckStep("sample_select", "pass", (time.perf_counter() - t0) * 1000, "ok")
        except Exception as exc:
            return HealthCheckStep("sample_select", "fail", 0.0, str(exc))

    def _step_latency(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            with self._connect() as conn:
                self._exec(conn, "SELECT 1", fetch_all=False)
            latency = (time.perf_counter() - t0) * 1000
            return HealthCheckStep("latency_probe", "pass", latency, f"{latency:.1f}ms")
        except Exception as exc:
            return HealthCheckStep("latency_probe", "fail", 0.0, str(exc))

    def _step_clock_skew(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            with self._connect() as conn:
                row = self._exec(conn, "SELECT current_timestamp()", fetch_all=False)
            db_now = row[0] if row else None
            local_now = datetime.datetime.now(datetime.timezone.utc)
            if isinstance(db_now, str):
                db_now = datetime.datetime.fromisoformat(db_now)
            if db_now is not None and db_now.tzinfo is None:
                db_now = db_now.replace(tzinfo=datetime.timezone.utc)
            if db_now is None:
                return HealthCheckStep("clock_skew", "fail", 0.0, "no timestamp returned")
            skew_s = abs((db_now - local_now).total_seconds())
            status = "pass" if skew_s < 60 else "fail"
            return HealthCheckStep("clock_skew", status, (time.perf_counter() - t0) * 1000, f"skew={skew_s:.1f}s")
        except Exception as exc:
            return HealthCheckStep("clock_skew", "fail", 0.0, str(exc))

    def list_schemas(self) -> list[str]:
        with self._connect() as conn:
            rows = self._exec(conn, "SHOW SCHEMAS")
        # SHOW SCHEMAS returns rows with databaseName in first column
        return sorted(row[0] for row in rows)

    def list_tables(self, schema: str) -> list[str]:
        with self._connect() as conn:
            rows = self._exec(conn, f"SHOW TABLES IN `{schema}`")
        # SHOW TABLES returns (database, tableName, isTemporary)
        return sorted(row[1] for row in rows)

    def describe_columns(self, schema: str, table: str) -> list[ColumnMeta]:
        # DESCRIBE TABLE returns (col_name, data_type, comment) — no position column.
        with self._connect() as conn:
            rows = self._exec(conn, f"DESCRIBE TABLE `{schema}`.`{table}`")
        return [
            ColumnMeta(name=row[0], data_type=row[1], nullable=True, position=i + 1)
            for i, row in enumerate(rows)
            if row[0] and not row[0].startswith("#")  # skip partition headers
        ]

    def sample(self, schema: str, table: str, n: int = 100_000) -> pd.DataFrame:
        # TABLESAMPLE (n ROWS) uses Delta's efficient sampling — avoids a full sort.
        with self._connect() as conn:
            df = self._exec_df(conn, f"SELECT * FROM `{schema}`.`{table}` TABLESAMPLE ({n} ROWS)")
        return df

    def aggregate(self, schema: str, table: str, exprs: list[AggExpr]) -> dict[str, Any]:
        cols = ", ".join(f"{e.sql} AS {e.name}" for e in exprs)
        with self._connect() as conn:
            df = self._exec_df(conn, f"SELECT {cols} FROM `{schema}`.`{table}`")
        if df.empty:
            return {e.name: None for e in exprs}
        row = df.iloc[0]
        return {e.name: row[e.name] for e in exprs}
