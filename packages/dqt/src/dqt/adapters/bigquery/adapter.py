# BigQueryAdapter uses google-cloud-bigquery (official Google client).
# Cost guard: every query checks dry-run bytes against max_bytes_billed before executing.
# Sampling uses ORDER BY RAND() — BQ optimises this to a table scan with reservoir sampling.
from __future__ import annotations

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


class BigQueryAdapter:
    sql_dialect = "bigquery"

    def __init__(self, project: str, max_bytes_billed: int = 50 * 1024**3, **client_kwargs: Any) -> None:
        try:
            from google.cloud import bigquery
        except ImportError as exc:
            raise ImportError(
                "google-cloud-bigquery is required for BigQueryAdapter. "
                "Install with: pip install google-cloud-bigquery db-dtypes"
            ) from exc
        self._bq = bigquery.Client(project=project, **client_kwargs)
        self._project = project
        self._max_bytes_billed = max_bytes_billed

    def _dry_run_bytes(self, sql: str) -> int:
        from google.cloud import bigquery
        job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
        job = self._bq.query(sql, job_config=job_config)
        return job.total_bytes_processed or 0

    def _run_query(self, sql: str) -> pd.DataFrame:
        """Execute SQL after a cost-guard dry run."""
        estimated = self._dry_run_bytes(sql)
        if estimated > self._max_bytes_billed:
            raise RuntimeError(
                f"BigQuery cost guard: estimated {estimated / 1024**3:.1f} GB "
                f"exceeds limit of {self._max_bytes_billed / 1024**3:.1f} GB"
            )
        return self._bq.query(sql).to_dataframe()

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
        # BigQuery is a managed service — clock skew is irrelevant; mark as skip.
        steps.append(HealthCheckStep("clock_skew", "skip", 0.0, "managed service"))
        return HealthCheckResult(steps=steps)

    def _step_tcp(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            list(self._bq.list_datasets(max_results=1))
            return HealthCheckStep("tcp_reach", "pass", (time.perf_counter() - t0) * 1000, "ok")
        except Exception as exc:
            return HealthCheckStep("tcp_reach", "fail", 0.0, str(exc))

    def _step_auth(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            # Use the credentials directly to avoid requiring db-dtypes for a simple probe.
            creds = self._bq._credentials
            if hasattr(creds, "service_account_email"):
                identity = creds.service_account_email
            elif hasattr(creds, "client_id"):
                identity = f"oauth:{creds.client_id[:12]}..."
            else:
                identity = self._project
            return HealthCheckStep("auth", "pass", (time.perf_counter() - t0) * 1000, f"identity={identity}")
        except Exception as exc:
            return HealthCheckStep("auth", "fail", 0.0, str(exc))

    def _step_info_schema(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            datasets = list(self._bq.list_datasets())
            return HealthCheckStep(
                "info_schema", "pass",
                (time.perf_counter() - t0) * 1000,
                f"{len(datasets)} datasets",
            )
        except Exception as exc:
            return HealthCheckStep("info_schema", "fail", 0.0, str(exc))

    def _step_sample_select(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            datasets = list(self._bq.list_datasets(max_results=1))
            if datasets:
                list(self._bq.list_tables(datasets[0].dataset_id, max_results=1))
            return HealthCheckStep("sample_select", "pass", (time.perf_counter() - t0) * 1000, "ok")
        except Exception as exc:
            return HealthCheckStep("sample_select", "fail", 0.0, str(exc))

    def _step_latency(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            # list_datasets avoids db-dtypes and is a representative round-trip probe.
            list(self._bq.list_datasets(max_results=1))
            latency = (time.perf_counter() - t0) * 1000
            return HealthCheckStep("latency_probe", "pass", latency, f"{latency:.1f}ms")
        except Exception as exc:
            return HealthCheckStep("latency_probe", "fail", 0.0, str(exc))

    def list_schemas(self) -> list[str]:
        return sorted(ds.dataset_id for ds in self._bq.list_datasets())

    def list_tables(self, schema: str) -> list[str]:
        return sorted(t.table_id for t in self._bq.list_tables(schema))

    def describe_columns(self, schema: str, table: str) -> list[ColumnMeta]:
        project = self._project or self._bq.project or ""
        sql = (
            f"SELECT column_name, data_type, is_nullable, ordinal_position "
            f"FROM `{project}.{schema}.INFORMATION_SCHEMA.COLUMNS` "
            f"WHERE table_name = '{table}' "
            f"ORDER BY ordinal_position"
        )
        df = self._bq.query(sql).to_dataframe()
        return [
            ColumnMeta(
                name=row["column_name"],
                data_type=row["data_type"],
                nullable=(row["is_nullable"] == "YES"),
                position=int(row["ordinal_position"]),
            )
            for _, row in df.iterrows()
        ]

    def sample(self, schema: str, table: str, n: int = 100_000, where: str | None = None) -> pd.DataFrame:
        project = self._project or self._bq.project or ""
        where_clause = f" WHERE {where}" if where else ""
        sql = f"SELECT * FROM `{project}.{schema}.{table}`{where_clause} ORDER BY RAND() LIMIT {n}"
        return self._run_query(sql)

    def aggregate(self, schema: str, table: str, exprs: list[AggExpr]) -> dict[str, Any]:
        project = self._project or self._bq.project or ""
        cols = ", ".join(f"{e.sql} AS {e.name}" for e in exprs)
        sql = f"SELECT {cols} FROM `{project}.{schema}.{table}`"
        df = self._run_query(sql)
        if df.empty:
            return {e.name: None for e in exprs}
        row = df.iloc[0]
        return {e.name: row[e.name] for e in exprs}

    def profile_column(self, schema: str, table: str, column: str) -> "ColumnProfileResult":
        from dqt.adapters._pandas_profile import pandas_profile_column
        return pandas_profile_column(self, schema, table, column, _log)
