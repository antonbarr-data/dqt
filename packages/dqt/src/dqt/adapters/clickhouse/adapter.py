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
    sql_dialect = "clickhouse"

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
            # toTimeZone converts to UTC regardless of server timezone
            db_now_str = self._client.command("SELECT toTimeZone(now(), 'UTC')")
            if isinstance(db_now_str, datetime.datetime):
                db_now = db_now_str
            else:
                db_now = datetime.datetime.fromisoformat(str(db_now_str))
            local_now = datetime.datetime.now(datetime.timezone.utc)
            db_utc = db_now.replace(tzinfo=datetime.timezone.utc)
            skew_s = abs((db_utc - local_now).total_seconds())
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

    def sample(self, schema: str, table: str, n: int = 100_000, where: str | None = None) -> pd.DataFrame:
        # ClickHouse rand() is fast — ORDER BY rand() on large tables can be expensive.
        # For production use, SAMPLE clause is preferable, but requires MergeTree engine.
        # We use ORDER BY rand() LIMIT n for correctness across all table engines.
        where_clause = f" WHERE {where}" if where else ""
        result = self._client.query(
            f"SELECT * FROM `{schema}`.`{table}`{where_clause} ORDER BY rand() LIMIT {n}"
        )
        return pd.DataFrame(result.result_rows, columns=result.column_names)

    def aggregate(self, schema: str, table: str, exprs: list[AggExpr]) -> dict[str, Any]:
        cols = ", ".join(f"{e.sql} AS {e.name}" for e in exprs)
        result = self._client.query(f"SELECT {cols} FROM `{schema}`.`{table}`")
        row = result.result_rows[0] if result.result_rows else [None] * len(exprs)
        return dict(zip([e.name for e in exprs], row))

    def profile_column(self, schema: str, table: str, column: str) -> "ColumnProfileResult":
        from dqt.adapters._protocol import ColumnProfileResult
        try:
            cols = self.describe_columns(schema, table)
            meta = next((c for c in cols if c.name == column), None)
            if meta is None:
                return ColumnProfileResult(column=column)

            data_type = meta.data_type
            base_type = data_type.replace("Nullable(", "").rstrip(")")
            is_numeric = any(t in base_type for t in ("Int", "Float", "Decimal", "UInt"))

            total_q = self._client.query(
                f"SELECT count(*) AS n, countIf(isNull(`{column}`)) AS nulls"
                f" FROM `{schema}`.`{table}`"
            )
            n_total = int(total_q.result_rows[0][0]) if total_q.result_rows else 0
            n_null = int(total_q.result_rows[0][1]) if total_q.result_rows else 0

            distinct_q = self._client.query(
                f"SELECT uniqExact(`{column}`) FROM `{schema}`.`{table}` WHERE isNotNull(`{column}`)"
            )
            n_distinct = int(distinct_q.result_rows[0][0]) if distinct_q.result_rows else 0

            if is_numeric:
                zero_q = self._client.query(
                    f"SELECT countIf(`{column}` = 0) FROM `{schema}`.`{table}` WHERE isNotNull(`{column}`)"
                )
                n_zero = int(zero_q.result_rows[0][0]) if zero_q.result_rows else 0

                stats_sql = (
                    f"SELECT toFloat64(min(`{column}`)), toFloat64(max(`{column}`)),"
                    f" toFloat64(avg(`{column}`)), toFloat64(stddevSamp(`{column}`)),"
                    f" toFloat64(quantileExact(0.02)(`{column}`)),"
                    f" toFloat64(quantileExact(0.05)(`{column}`)),"
                    f" toFloat64(quantileExact(0.10)(`{column}`)),"
                    f" toFloat64(quantileExact(0.25)(`{column}`)),"
                    f" toFloat64(quantileExact(0.50)(`{column}`)),"
                    f" toFloat64(quantileExact(0.75)(`{column}`)),"
                    f" toFloat64(quantileExact(0.90)(`{column}`)),"
                    f" toFloat64(quantileExact(0.95)(`{column}`)),"
                    f" toFloat64(quantileExact(0.98)(`{column}`)),"
                    f" toFloat64(quantileExact(0.99)(`{column}`))"
                    f" FROM `{schema}`.`{table}` WHERE isNotNull(`{column}`)"
                )
                sr = self._client.query(stats_sql)
                row = sr.result_rows[0] if sr.result_rows else [None] * 14
                mn, mx, mean, std = row[0], row[1], row[2], row[3]
                p2, p5, p10, p25, p50, p75, p90, p95, p98, p99 = (
                    row[4], row[5], row[6], row[7], row[8],
                    row[9], row[10], row[11], row[12], row[13]
                )

                buckets: list[dict] = []
                if p2 is not None and p98 is not None and p98 > p2:
                    bw = (p98 - p2) / 20
                    iqr = (p75 or 0) - (p25 or 0)
                    fence_lo = (p25 or 0) - 1.5 * iqr
                    fence_hi = (p75 or 0) + 1.5 * iqr
                    hist_sql = (
                        f"SELECT multiIf(`{column}` < {p2}, -1,"
                        f" `{column}` >= {p98}, 20,"
                        f" toInt32(floor((`{column}` - {p2}) / {bw}))) AS bi,"
                        f" count(*) AS freq"
                        f" FROM `{schema}`.`{table}` WHERE isNotNull(`{column}`)"
                        f" GROUP BY bi ORDER BY bi"
                    )
                    counts = {int(r[0]): int(r[1]) for r in self._client.query(hist_sql).result_rows}
                    for i in range(20):
                        lower = p2 + i * bw
                        upper = p2 + (i + 1) * bw
                        buckets.append({
                            "lower": round(lower, 6), "upper": round(upper, 6),
                            "count": counts.get(i, 0),
                            "is_outlier": upper <= fence_lo or lower >= fence_hi,
                        })

                non_null = n_total - n_null
                top_q = self._client.query(
                    f"SELECT toString(`{column}`), count(*)"
                    f" FROM `{schema}`.`{table}` WHERE isNotNull(`{column}`)"
                    f" GROUP BY `{column}` ORDER BY count(*) DESC LIMIT 15"
                )
                top_values = [
                    {"value": str(r[0]), "count": int(r[1]),
                     "pct": round(int(r[1]) / non_null, 4) if non_null > 0 else 0}
                    for r in top_q.result_rows
                ]
                return ColumnProfileResult(
                    column=column, kind="numeric", data_type=data_type,
                    nullable=meta.nullable, position=meta.position,
                    total_count=n_total, null_count=n_null,
                    zero_count=n_zero, empty_count=0, distinct_count=n_distinct,
                    p_min=mn, p_max=mx, p_mean=mean, p_stddev=std,
                    p2=p2, p5=p5, p10=p10, p25=p25, p50=p50,
                    p75=p75, p90=p90, p95=p95, p98=p98, p99=p99,
                    histogram=buckets, top_values=top_values,
                )
            else:
                empty_q = self._client.query(
                    f"SELECT countIf(trim(toString(`{column}`)) = '')"
                    f" FROM `{schema}`.`{table}` WHERE isNotNull(`{column}`)"
                )
                n_empty = int(empty_q.result_rows[0][0]) if empty_q.result_rows else 0
                non_null = n_total - n_null
                top_q = self._client.query(
                    f"SELECT toString(`{column}`), count(*)"
                    f" FROM `{schema}`.`{table}` WHERE isNotNull(`{column}`)"
                    f" GROUP BY `{column}` ORDER BY count(*) DESC LIMIT 20"
                )
                top_values = [
                    {"value": str(r[0]), "count": int(r[1]),
                     "pct": round(int(r[1]) / non_null, 4) if non_null > 0 else 0}
                    for r in top_q.result_rows
                ]
                return ColumnProfileResult(
                    column=column, kind="categorical", data_type=data_type,
                    nullable=meta.nullable, position=meta.position,
                    total_count=n_total, null_count=n_null,
                    zero_count=0, empty_count=n_empty, distinct_count=n_distinct,
                    top_values=top_values,
                )
        except Exception as exc:
            _log.error("clickhouse profile_column failed", column=column, error=str(exc))
            return ColumnProfileResult(column=column)
