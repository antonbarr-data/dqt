# Column Profile Page Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the column profile page from a single-column stats summary into a full two-panel analytics view with live warehouse stats, completeness panel, distribution, top values, schema history, lineage, freshness/volume, incidents, and seasonality.

**Architecture:** Two-column CSS grid (70/30). Stats are cached in a new `column_stats_cache` DB table, populated on-demand by the existing profile endpoint (which also saves to cache). Schema history tracked diff-only in `column_schema_history`. All new panels are separate React components mounted into the left column or right sidebar.

**Tech Stack:** Next.js 14 App Router, `"use client"`, React SVG charts, FastAPI + SQLAlchemy 2.x async, adapter protocol extension across 6 adapters.

---

## File Map

**New files:**
- `apps/server/src/dqt_server/api/v1/column_profile.py` — all new endpoints
- `apps/web/src/components/column-profile/time-series-panel.tsx`
- `apps/web/src/components/column-profile/completeness-panel.tsx`
- `apps/web/src/components/column-profile/distribution-panel.tsx`
- `apps/web/src/components/column-profile/top-values-panel.tsx`
- `apps/web/src/components/column-profile/schema-panel.tsx`
- `apps/web/src/components/column-profile/lineage-panel.tsx`
- `apps/web/src/components/column-profile/incidents-panel.tsx`
- `apps/web/src/components/column-profile/seasonality-panel.tsx`

**Modified files:**
- `apps/server/src/dqt_server/models/core.py` — add 2 new ORM models
- `apps/server/src/dqt_server/main.py` — register new router
- `packages/dqt/src/dqt/adapters/_protocol.py` — add `profile_column` to protocol
- `packages/dqt/src/dqt/adapters/clickhouse/adapter.py` — implement `profile_column`
- `packages/dqt/src/dqt/adapters/postgres/adapter.py` — implement `profile_column`
- `packages/dqt/src/dqt/adapters/snowflake/adapter.py` — implement `profile_column`
- `packages/dqt/src/dqt/adapters/bigquery/adapter.py` — implement `profile_column`
- `packages/dqt/src/dqt/adapters/databricks/adapter.py` — implement `profile_column`
- `packages/dqt/src/dqt/adapters/local/adapter.py` — implement `profile_column`
- `apps/server/src/dqt_server/check_runner.py` — update to use adapter.profile_column + schema history tracking
- `apps/web/src/app/(app)/datasets/[id]/[column]/page.tsx` — major rewrite

---

## Task 1: DB models — ColumnStatsCache + ColumnSchemaHistory

**Files:**
- Modify: `apps/server/src/dqt_server/models/core.py`

- [ ] **Step 1: Add two new ORM models at the end of core.py**

```python
class ColumnStatsCache(Base):
    __tablename__ = "column_stats_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    column_name: Mapped[str] = mapped_column(String, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False, default="unknown")  # "numeric" | "categorical"
    data_type: Mapped[str | None] = mapped_column(String, nullable=True)
    nullable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    null_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    zero_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    empty_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    distinct_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    p_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    p_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    p_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    p_stddev: Mapped[float | None] = mapped_column(Float, nullable=True)
    p2: Mapped[float | None] = mapped_column(Float, nullable=True)
    p5: Mapped[float | None] = mapped_column(Float, nullable=True)
    p10: Mapped[float | None] = mapped_column(Float, nullable=True)
    p25: Mapped[float | None] = mapped_column(Float, nullable=True)
    p50: Mapped[float | None] = mapped_column(Float, nullable=True)
    p75: Mapped[float | None] = mapped_column(Float, nullable=True)
    p90: Mapped[float | None] = mapped_column(Float, nullable=True)
    p95: Mapped[float | None] = mapped_column(Float, nullable=True)
    p98: Mapped[float | None] = mapped_column(Float, nullable=True)
    p99: Mapped[float | None] = mapped_column(Float, nullable=True)
    histogram: Mapped[list | None] = mapped_column(JSONB, nullable=True)   # [{lower, upper, count, is_outlier}]
    top_values: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # [{value, count, pct}]

    __table_args__ = (
        __import__("sqlalchemy").UniqueConstraint("dataset_id", "column_name", name="uq_col_stats"),
    )


class ColumnSchemaHistory(Base):
    __tablename__ = "column_schema_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    column_name: Mapped[str] = mapped_column(String, nullable=False)
    data_type: Mapped[str | None] = mapped_column(String, nullable=True)
    nullable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
```

- [ ] **Step 2: Verify the models import correctly**

```bash
cd apps/server
python -c "from dqt_server.models.core import ColumnStatsCache, ColumnSchemaHistory; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Restart the server to apply create_all (tables are created automatically)**

`Base.metadata.create_all` runs on startup — no manual migration needed for new tables.

- [ ] **Step 4: Commit**

```bash
git add apps/server/src/dqt_server/models/core.py
git commit -m "feat(db): add column_stats_cache and column_schema_history tables"
```

---

## Task 2: Adapter protocol — add profile_column

**Files:**
- Modify: `packages/dqt/src/dqt/adapters/_protocol.py`

- [ ] **Step 1: Add ColumnProfileResult dataclass and profile_column to the protocol**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

import pandas as pd


@dataclass
class AggExpr:
    name: str
    sql: str


@dataclass
class HealthCheckStep:
    name: str
    status: Literal["pass", "fail", "skip"]
    latency_ms: float
    detail: str


@dataclass
class HealthCheckResult:
    steps: list[HealthCheckStep] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(s.status in ("pass", "skip") for s in self.steps)


@dataclass
class ColumnMeta:
    name: str
    data_type: str
    nullable: bool
    position: int


@dataclass
class ColumnProfileResult:
    column: str
    kind: str = "unknown"          # "numeric" | "categorical" | "unknown"
    data_type: str = ""
    nullable: bool = True
    position: int = 0
    total_count: int = 0
    null_count: int = 0
    zero_count: int = 0
    empty_count: int = 0
    distinct_count: int = 0
    # numeric stats (None for categorical)
    p_min: float | None = None
    p_max: float | None = None
    p_mean: float | None = None
    p_stddev: float | None = None
    p2: float | None = None
    p5: float | None = None
    p10: float | None = None
    p25: float | None = None
    p50: float | None = None
    p75: float | None = None
    p90: float | None = None
    p95: float | None = None
    p98: float | None = None
    p99: float | None = None
    histogram: list[dict[str, Any]] = field(default_factory=list)   # [{lower, upper, count, is_outlier}]
    top_values: list[dict[str, Any]] = field(default_factory=list)  # [{value, count, pct}]


@runtime_checkable
class WarehouseAdapter(Protocol):
    sql_dialect: str  # "bigquery" | "postgres" | "clickhouse" | "duckdb" | "ansi"

    def health_check(self) -> HealthCheckResult: ...
    def sample(self, schema: str, table: str, n: int = 100_000, where: str | None = None) -> pd.DataFrame: ...
    def aggregate(self, schema: str, table: str, exprs: list[AggExpr]) -> dict[str, object]: ...
    def describe_columns(self, schema: str, table: str) -> list[ColumnMeta]: ...
    def list_schemas(self) -> list[str]: ...
    def list_tables(self, schema: str) -> list[str]: ...
    def profile_column(self, schema: str, table: str, column: str) -> ColumnProfileResult: ...
```

- [ ] **Step 2: Run import check**

```bash
cd packages/dqt
python -c "from dqt.adapters._protocol import ColumnProfileResult, WarehouseAdapter; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add packages/dqt/src/dqt/adapters/_protocol.py
git commit -m "feat(adapters): add ColumnProfileResult + profile_column to WarehouseAdapter protocol"
```

---

## Task 3: ClickHouse adapter — implement profile_column

**Files:**
- Modify: `packages/dqt/src/dqt/adapters/clickhouse/adapter.py`

- [ ] **Step 1: Read the file to find the class structure**

Look for the `ClickHouseAdapter` class and where other methods like `aggregate` or `describe_columns` are defined. The existing `check_runner._numeric_profile` / `_categorical_profile` logic moves here.

- [ ] **Step 2: Add `profile_column` method to ClickHouseAdapter**

```python
def profile_column(self, schema: str, table: str, column: str) -> ColumnProfileResult:
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
                row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13]
            )

            n_bins, lo, hi = 20, p2, p98
            buckets: list[dict] = []
            if hi is not None and lo is not None and hi > lo:
                bw = (hi - lo) / n_bins
                iqr = (p75 or 0) - (p25 or 0)
                fence_lo = (p25 or 0) - 1.5 * iqr
                fence_hi = (p75 or 0) + 1.5 * iqr
                hist_sql = (
                    f"SELECT multiIf(`{column}` < {lo}, -1,"
                    f" `{column}` >= {hi}, {n_bins},"
                    f" toInt32(floor((`{column}` - {lo}) / {bw}))) AS bi,"
                    f" count(*) AS freq"
                    f" FROM `{schema}`.`{table}` WHERE isNotNull(`{column}`)"
                    f" GROUP BY bi ORDER BY bi"
                )
                counts = {int(r[0]): int(r[1]) for r in self._client.query(hist_sql).result_rows}
                for i in range(n_bins):
                    lower = lo + i * bw
                    upper = lo + (i + 1) * bw
                    buckets.append({
                        "lower": round(lower, 6), "upper": round(upper, 6),
                        "count": counts.get(i, 0),
                        "is_outlier": upper <= fence_lo or lower >= fence_hi,
                    })

            top_q = self._client.query(
                f"SELECT toString(`{column}`), count(*)"
                f" FROM `{schema}`.`{table}` WHERE isNotNull(`{column}`)"
                f" GROUP BY `{column}` ORDER BY count(*) DESC LIMIT 15"
            )
            non_null = n_total - n_null
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
            top_q = self._client.query(
                f"SELECT toString(`{column}`), count(*)"
                f" FROM `{schema}`.`{table}` WHERE isNotNull(`{column}`)"
                f" GROUP BY `{column}` ORDER BY count(*) DESC LIMIT 20"
            )
            non_null = n_total - n_null
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
        import logging
        logging.getLogger(__name__).error("clickhouse profile_column failed: %s", exc)
        return ColumnProfileResult(column=column)
```

- [ ] **Step 3: Run existing ClickHouse adapter tests**

```bash
cd packages/dqt
pytest tests/ -k "clickhouse" -v --tb=short 2>&1 | head -30
```

- [ ] **Step 4: Commit**

```bash
git add packages/dqt/src/dqt/adapters/clickhouse/adapter.py
git commit -m "feat(clickhouse): implement profile_column"
```

---

## Task 4: Postgres adapter — implement profile_column

**Files:**
- Modify: `packages/dqt/src/dqt/adapters/postgres/adapter.py`

- [ ] **Step 1: Read the file to understand the adapter structure (how _client / execute works)**

- [ ] **Step 2: Add `profile_column` method using standard SQL percentile functions**

```python
def profile_column(self, schema: str, table: str, column: str) -> ColumnProfileResult:
    from dqt.adapters._protocol import ColumnProfileResult
    import pandas as pd
    try:
        cols = self.describe_columns(schema, table)
        meta = next((c for c in cols if c.name == column), None)
        if meta is None:
            return ColumnProfileResult(column=column)

        data_type = meta.data_type
        numeric_types = ("int", "float", "numeric", "decimal", "double", "real", "bigint",
                         "smallint", "money", "serial")
        is_numeric = any(t in data_type.lower() for t in numeric_types)

        df = self.sample(schema, table, n=200_000)
        if column not in df.columns:
            return ColumnProfileResult(column=column)

        col = df[column]
        n_total = len(col)
        n_null = int(col.isna().sum())
        non_null = col.dropna()
        n_distinct = int(non_null.nunique())

        if is_numeric:
            numeric_col = pd.to_numeric(non_null, errors="coerce").dropna()
            n_zero = int((numeric_col == 0).sum())
            p_min = float(numeric_col.min()) if len(numeric_col) > 0 else None
            p_max = float(numeric_col.max()) if len(numeric_col) > 0 else None
            p_mean = float(numeric_col.mean()) if len(numeric_col) > 0 else None
            p_stddev = float(numeric_col.std()) if len(numeric_col) > 1 else None
            quantiles = numeric_col.quantile([0.02,0.05,0.10,0.25,0.50,0.75,0.90,0.95,0.98,0.99])
            p2,p5,p10,p25,p50,p75,p90,p95,p98,p99 = (
                float(quantiles[q]) for q in [0.02,0.05,0.10,0.25,0.50,0.75,0.90,0.95,0.98,0.99]
            )
            # histogram over p2-p98 range
            buckets: list[dict] = []
            if p2 < p98:
                iqr = p75 - p25
                fence_lo = p25 - 1.5 * iqr
                fence_hi = p75 + 1.5 * iqr
                n_bins = 20
                bw = (p98 - p2) / n_bins
                clipped = numeric_col.clip(p2, p98 - 1e-9)
                bin_idx = ((clipped - p2) / bw).astype(int).clip(0, n_bins - 1)
                counts = bin_idx.value_counts().to_dict()
                for i in range(n_bins):
                    lower = p2 + i * bw
                    upper = p2 + (i + 1) * bw
                    buckets.append({
                        "lower": round(lower, 6), "upper": round(upper, 6),
                        "count": int(counts.get(i, 0)),
                        "is_outlier": upper <= fence_lo or lower >= fence_hi,
                    })
            top_q = non_null.value_counts().head(15)
            top_values = [
                {"value": str(v), "count": int(c),
                 "pct": round(int(c) / len(non_null), 4) if len(non_null) > 0 else 0}
                for v, c in top_q.items()
            ]
            return ColumnProfileResult(
                column=column, kind="numeric", data_type=data_type,
                nullable=meta.nullable, position=meta.position,
                total_count=n_total, null_count=n_null,
                zero_count=n_zero, empty_count=0, distinct_count=n_distinct,
                p_min=p_min, p_max=p_max, p_mean=p_mean, p_stddev=p_stddev,
                p2=p2, p5=p5, p10=p10, p25=p25, p50=p50,
                p75=p75, p90=p90, p95=p95, p98=p98, p99=p99,
                histogram=buckets, top_values=top_values,
            )
        else:
            str_col = non_null.astype(str)
            n_empty = int((str_col.str.strip() == "").sum())
            top_q = str_col.value_counts().head(20)
            top_values = [
                {"value": str(v), "count": int(c),
                 "pct": round(int(c) / len(non_null), 4) if len(non_null) > 0 else 0}
                for v, c in top_q.items()
            ]
            return ColumnProfileResult(
                column=column, kind="categorical", data_type=data_type,
                nullable=meta.nullable, position=meta.position,
                total_count=n_total, null_count=n_null,
                zero_count=0, empty_count=n_empty, distinct_count=n_distinct,
                top_values=top_values,
            )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("postgres profile_column failed: %s", exc)
        return ColumnProfileResult(column=column)
```

Note: Postgres uses the pandas-based approach (sample then compute) because it avoids dialect-specific SQL for percentiles. For large tables the 200k sample is the same strategy the check algorithms use.

- [ ] **Step 3: Commit**

```bash
git add packages/dqt/src/dqt/adapters/postgres/adapter.py
git commit -m "feat(postgres): implement profile_column via sample+pandas"
```

---

## Task 5: Snowflake, BigQuery, Databricks, Local adapters — profile_column

**Files:**
- Modify: `packages/dqt/src/dqt/adapters/snowflake/adapter.py`
- Modify: `packages/dqt/src/dqt/adapters/bigquery/adapter.py`
- Modify: `packages/dqt/src/dqt/adapters/databricks/adapter.py`
- Modify: `packages/dqt/src/dqt/adapters/local/adapter.py`

All four use the **same pandas-based implementation** as Postgres (sample + compute stats in Python). Copy the Postgres `profile_column` method verbatim into each adapter.

- [ ] **Step 1: Add identical `profile_column` to SnowflakeAdapter**

Copy the Postgres implementation into `snowflake/adapter.py`. Only difference: error log message says "snowflake".

- [ ] **Step 2: Add identical `profile_column` to BigQueryAdapter**

Same. Error log says "bigquery".

- [ ] **Step 3: Add identical `profile_column` to DatabricksAdapter**

Same. Error log says "databricks".

- [ ] **Step 4: Add `profile_column` to LocalAdapter**

Local adapter uses DuckDB/pandas directly. Identical implementation. Error log says "local".

- [ ] **Step 5: Verify protocol compliance**

```bash
cd packages/dqt
python -c "
from dqt.adapters._protocol import WarehouseAdapter
from dqt.adapters.clickhouse.adapter import ClickHouseAdapter
from dqt.adapters.postgres.adapter import PostgresAdapter
for cls in [ClickHouseAdapter, PostgresAdapter]:
    print(cls.__name__, isinstance(cls, type) and hasattr(cls, 'profile_column'))
"
```

Expected: both print `True`.

- [ ] **Step 6: Commit**

```bash
git add packages/dqt/src/dqt/adapters/
git commit -m "feat(adapters): implement profile_column in all warehouse adapters"
```

---

## Task 6: Backend API — column_profile router

**Files:**
- Create: `apps/server/src/dqt_server/api/v1/column_profile.py`
- Modify: `apps/server/src/dqt_server/main.py`

This task adds 4 new endpoints:
- `GET /datasets/{id}/columns/{col}/stats` — returns cached stats or computes fresh
- `POST /datasets/{id}/columns/{col}/refresh-stats` — force recompute + save to cache
- `GET /datasets/{id}/columns/{col}/schema-history` — returns schema changelog
- `GET /datasets/{id}/columns/{col}/incidents` — returns incidents for this column

- [ ] **Step 1: Create `column_profile.py`**

```python
"""Column profile endpoints — stats cache, schema history, incidents."""
from __future__ import annotations

import asyncio
from dataclasses import asdict
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from dqt_server.check_runner import _make_adapter, _default_schema_for_source, check_runner
from dqt_server.db.engine import get_db
from dqt_server.models.core import (
    ColumnSchemaHistory, ColumnStatsCache, Dataset, Incident, Source,
)

log = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["column-profile"])


async def _get_dataset_and_source(dataset_id: str, db: AsyncSession) -> tuple[Dataset, Source]:
    d = await db.get(Dataset, dataset_id)
    if d is None:
        raise HTTPException(404, detail=f"Dataset '{dataset_id}' not found")
    s = await db.get(Source, d.source_id)
    if s is None:
        raise HTTPException(404, detail=f"Source not found")
    return d, s


def _stats_to_dict(row: ColumnStatsCache) -> dict:
    return {
        "computed_at": row.computed_at.isoformat(),
        "kind": row.kind,
        "data_type": row.data_type,
        "nullable": row.nullable,
        "position": row.position,
        "total_count": row.total_count,
        "null_count": row.null_count,
        "zero_count": row.zero_count,
        "empty_count": row.empty_count,
        "distinct_count": row.distinct_count,
        "p_min": row.p_min, "p_max": row.p_max,
        "p_mean": row.p_mean, "p_stddev": row.p_stddev,
        "p2": row.p2, "p5": row.p5, "p10": row.p10,
        "p25": row.p25, "p50": row.p50, "p75": row.p75,
        "p90": row.p90, "p95": row.p95, "p98": row.p98, "p99": row.p99,
        "histogram": row.histogram or [],
        "top_values": row.top_values or [],
    }


async def _compute_and_save_stats(
    dataset_id: str, column: str, db: AsyncSession
) -> ColumnStatsCache:
    d, s = await _get_dataset_and_source(dataset_id, db)
    schema = _default_schema_for_source(s)
    # table is the last segment of dataset_id (e.g. "db.schema.table" -> "table")
    table = dataset_id.split(".")[-1]
    loop = asyncio.get_event_loop()
    adapter = await loop.run_in_executor(None, _make_adapter, s)
    result = await loop.run_in_executor(
        None, adapter.profile_column, schema, table, column
    )

    existing_q = await db.execute(
        select(ColumnStatsCache)
        .where(ColumnStatsCache.dataset_id == dataset_id)
        .where(ColumnStatsCache.column_name == column)
    )
    row = existing_q.scalar_one_or_none()
    if row is None:
        row = ColumnStatsCache(dataset_id=dataset_id, column_name=column)
        db.add(row)

    row.computed_at = datetime.now(timezone.utc)
    row.kind = result.kind
    row.data_type = result.data_type or None
    row.nullable = result.nullable
    row.position = result.position
    row.total_count = result.total_count
    row.null_count = result.null_count
    row.zero_count = result.zero_count
    row.empty_count = result.empty_count
    row.distinct_count = result.distinct_count
    row.p_min = result.p_min
    row.p_max = result.p_max
    row.p_mean = result.p_mean
    row.p_stddev = result.p_stddev
    row.p2 = result.p2
    row.p5 = result.p5
    row.p10 = result.p10
    row.p25 = result.p25
    row.p50 = result.p50
    row.p75 = result.p75
    row.p90 = result.p90
    row.p95 = result.p95
    row.p98 = result.p98
    row.p99 = result.p99
    row.histogram = result.histogram
    row.top_values = result.top_values

    await db.commit()
    await db.refresh(row)

    # Update schema history (Option B: write only on change)
    last_schema_q = await db.execute(
        select(ColumnSchemaHistory)
        .where(ColumnSchemaHistory.dataset_id == dataset_id)
        .where(ColumnSchemaHistory.column_name == column)
        .order_by(desc(ColumnSchemaHistory.recorded_at))
        .limit(1)
    )
    last = last_schema_q.scalar_one_or_none()
    changed = (
        last is None
        or last.data_type != result.data_type
        or last.nullable != result.nullable
        or last.position != result.position
    )
    if changed:
        db.add(ColumnSchemaHistory(
            dataset_id=dataset_id,
            column_name=column,
            data_type=result.data_type or None,
            nullable=result.nullable,
            position=result.position,
        ))
        await db.commit()

    return row


@router.get("/datasets/{dataset_id}/columns/{column}/stats")
async def get_column_stats(
    dataset_id: str,
    column: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return cached column stats. If not cached, computes from warehouse and saves."""
    existing_q = await db.execute(
        select(ColumnStatsCache)
        .where(ColumnStatsCache.dataset_id == dataset_id)
        .where(ColumnStatsCache.column_name == column)
    )
    row = existing_q.scalar_one_or_none()
    if row is not None:
        return _stats_to_dict(row)
    # Not cached yet — compute now
    row = await _compute_and_save_stats(dataset_id, column, db)
    return _stats_to_dict(row)


@router.post("/datasets/{dataset_id}/columns/{column}/refresh-stats", status_code=200)
async def refresh_column_stats(
    dataset_id: str,
    column: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Force recompute stats from warehouse and update cache."""
    row = await _compute_and_save_stats(dataset_id, column, db)
    return _stats_to_dict(row)


@router.get("/datasets/{dataset_id}/columns/{column}/schema-history")
async def get_column_schema_history(
    dataset_id: str,
    column: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    q = await db.execute(
        select(ColumnSchemaHistory)
        .where(ColumnSchemaHistory.dataset_id == dataset_id)
        .where(ColumnSchemaHistory.column_name == column)
        .order_by(ColumnSchemaHistory.recorded_at)
    )
    return [
        {
            "id": r.id,
            "data_type": r.data_type,
            "nullable": r.nullable,
            "position": r.position,
            "recorded_at": r.recorded_at.isoformat(),
        }
        for r in q.scalars().all()
    ]


@router.get("/datasets/{dataset_id}/columns/{column}/incidents")
async def get_column_incidents(
    dataset_id: str,
    column: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    q = await db.execute(
        select(Incident)
        .where(Incident.dataset_id == dataset_id)
        .where(Incident.column_name == column)
        .order_by(desc(Incident.opened_at))
        .limit(limit)
    )
    return [
        {
            "id": r.id,
            "detector_slug": r.detector_slug,
            "severity": r.severity,
            "message": r.message,
            "status": r.status,
            "opened_at": r.opened_at.isoformat(),
            "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
        }
        for r in q.scalars().all()
    ]
```

- [ ] **Step 2: Register the router in `main.py`**

Find where other routers are registered and add:

```python
from dqt_server.api.v1 import column_profile
app.include_router(column_profile.router)
```

- [ ] **Step 3: Test the stats endpoint manually**

Start the server and call:
```
GET /api/v1/datasets/{some_dataset_id}/columns/{some_column}/stats
```
Expected: JSON with stats fields.

- [ ] **Step 4: Commit**

```bash
git add apps/server/src/dqt_server/api/v1/column_profile.py apps/server/src/dqt_server/main.py
git commit -m "feat(api): column stats cache, schema history, and incidents endpoints"
```

---

## Task 7: Frontend — page layout + header

**Files:**
- Modify: `apps/web/src/app/(app)/datasets/[id]/[column]/page.tsx`

Major rewrite. The page becomes a layout shell that fetches data and passes it to panel components. Remove all inline panel code — each panel becomes its own component file.

- [ ] **Step 1: Replace the page with the two-column layout shell**

Key changes:
- Two-column CSS grid: `grid-template-columns: 1fr 380px`
- New header: breadcrumb, column name, type badge, DQT score, row count, last computed, refresh button
- Fetch data with `useEffect`: history, checks, stats (new), schema-history (new), incidents (new)
- Pass data as props to panel components (all imported dynamically with `ssr: false`)

```tsx
"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";
import { Loader2, RefreshCw } from "lucide-react";

// All panels are dynamic to avoid SSR issues
const TimeSeriesPanel = dynamic(() => import("@/components/column-profile/time-series-panel").then(m => m.TimeSeriesPanel), { ssr: false });
const CompletenessPanel = dynamic(() => import("@/components/column-profile/completeness-panel").then(m => m.CompletenessPanel), { ssr: false });
const DistributionPanel = dynamic(() => import("@/components/column-profile/distribution-panel").then(m => m.DistributionPanel), { ssr: false });
const TopValuesPanel = dynamic(() => import("@/components/column-profile/top-values-panel").then(m => m.TopValuesPanel), { ssr: false });
const SchemaPanel = dynamic(() => import("@/components/column-profile/schema-panel").then(m => m.SchemaPanel), { ssr: false });
const LineagePanel = dynamic(() => import("@/components/column-profile/lineage-panel").then(m => m.LineagePanel), { ssr: false });
const IncidentsPanel = dynamic(() => import("@/components/column-profile/incidents-panel").then(m => m.IncidentsPanel), { ssr: false });
const SeasonalityPanel = dynamic(() => import("@/components/column-profile/seasonality-panel").then(m => m.SeasonalityPanel), { ssr: false });
const SuggestPanel = dynamic(() => import("@/components/checks/suggest-panel").then(m => m.SuggestPanel), { ssr: false });

// ... [types remain same as before: RunPoint, ColumnCheck]

interface ColStats {
  computed_at: string;
  kind: string;
  data_type: string | null;
  nullable: boolean | null;
  position: number | null;
  total_count: number | null;
  null_count: number | null;
  zero_count: number | null;
  empty_count: number | null;
  distinct_count: number | null;
  p_min: number | null; p_max: number | null; p_mean: number | null; p_stddev: number | null;
  p2: number | null; p5: number | null; p10: number | null; p25: number | null;
  p50: number | null; p75: number | null; p90: number | null; p95: number | null;
  p98: number | null; p99: number | null;
  histogram: Array<{lower: number; upper: number; count: number; is_outlier: boolean}>;
  top_values: Array<{value: string; count: number; pct: number}>;
}

interface SchemaEntry {
  id: number;
  data_type: string | null;
  nullable: boolean | null;
  position: number | null;
  recorded_at: string;
}

interface ColIncident {
  id: number;
  detector_slug: string;
  severity: string;
  message: string;
  status: string;
  opened_at: string;
  resolved_at: string | null;
}

export default function ColumnProfilePage() {
  const params = useParams<{ id: string; column: string }>();
  const datasetId = decodeURIComponent(params.id);
  const column = decodeURIComponent(params.column);
  const enc = encodeURIComponent;

  const [history, setHistory] = useState<RunPoint[]>([]);
  const [checks, setChecks] = useState<ColumnCheck[]>([]);
  const [stats, setStats] = useState<ColStats | null>(null);
  const [schemaHistory, setSchemaHistory] = useState<SchemaEntry[]>([]);
  const [incidents, setIncidents] = useState<ColIncident[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [loadingStats, setLoadingStats] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showSuggest, setShowSuggest] = useState(false);

  const fetchChecks = useCallback(() => {
    fetch(`/api/v1/datasets/${enc(datasetId)}/columns/${enc(column)}/checks`)
      .then(r => r.ok ? r.json() : [])
      .then(setChecks).catch(() => {});
  }, [datasetId, column]);

  useEffect(() => {
    // History
    fetch(`/api/v1/datasets/${enc(datasetId)}/columns/${enc(column)}/history`)
      .then(r => r.ok ? r.json() : [])
      .then((d: RunPoint[]) => { setHistory(d); setLoadingHistory(false); })
      .catch(() => setLoadingHistory(false));

    fetchChecks();

    // Stats (may take time if not cached)
    fetch(`/api/v1/datasets/${enc(datasetId)}/columns/${enc(column)}/stats`)
      .then(r => r.ok ? r.json() : null)
      .then(setStats).catch(() => {})
      .finally(() => setLoadingStats(false));

    // Schema history
    fetch(`/api/v1/datasets/${enc(datasetId)}/columns/${enc(column)}/schema-history`)
      .then(r => r.ok ? r.json() : [])
      .then(setSchemaHistory).catch(() => {});

    // Incidents
    fetch(`/api/v1/datasets/${enc(datasetId)}/columns/${enc(column)}/incidents`)
      .then(r => r.ok ? r.json() : [])
      .then(setIncidents).catch(() => {});
  }, [datasetId, column, fetchChecks]);

  async function handleRefreshStats() {
    setRefreshing(true);
    try {
      const r = await fetch(
        `/api/v1/datasets/${enc(datasetId)}/columns/${enc(column)}/refresh-stats`,
        { method: "POST" }
      );
      if (r.ok) setStats(await r.json());
    } finally {
      setRefreshing(false);
    }
  }

  // Derived
  const latestByDetector = useMemo(() => {
    const m = new Map<string, RunPoint>();
    for (const r of [...history].sort((a, b) => new Date(b.ran_at).getTime() - new Date(a.ran_at).getTime())) {
      if (!m.has(r.detector)) m.set(r.detector, r);
    }
    return m;
  }, [history]);

  const worstVerdict = useMemo(() => {
    const RANK: Record<string, number> = { fail: 3, error: 3, warn: 2, pass: 1 };
    let worst: string | null = null;
    for (const r of Array.from(latestByDetector.values())) {
      const v = r.verdict ?? "pending";
      if (!worst || (RANK[v] ?? 0) > (RANK[worst] ?? 0)) worst = v;
    }
    return worst ?? "pending";
  }, [latestByDetector]);

  const dqtScore = useMemo(() => {
    const verdicts = Array.from(latestByDetector.values()).map(r => r.verdict ?? "pending");
    const ran = verdicts.filter(v => v !== "pending");
    if (ran.length === 0) return null;
    const total = ran.reduce((sum, v) => sum + (v === "pass" ? 100 : v === "warn" ? 50 : 0), 0);
    return Math.round(total / ran.length);
  }, [latestByDetector]);

  return (
    <div className="flex flex-col h-full overflow-auto">
      <div className="p-5" style={{ maxWidth: 1400 }}>
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 mb-4">
          <Link href="/datasets" className="t-small hover:opacity-80 transition-colors" style={{ color: "var(--accent)", fontFamily: "var(--font-jetbrains-mono)" }}>
            ← Datasets
          </Link>
          <span style={{ color: "var(--fg-3)", fontSize: 12 }}>/</span>
          <Link href={`/datasets/${enc(datasetId)}` as never} className="t-small font-mono hover:opacity-80 truncate" style={{ color: "var(--accent)", maxWidth: 200 }}>
            {datasetId}
          </Link>
          <span style={{ color: "var(--fg-3)", fontSize: 12 }}>/</span>
          <span className="t-small font-mono" style={{ color: "var(--fg-2)" }}>{column}</span>
        </div>

        {/* Header */}
        <div className="flex items-center gap-3 mb-5 flex-wrap">
          <h1 className="font-mono" style={{ fontSize: 22, fontWeight: 300, color: "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)", letterSpacing: "-0.02em" }}>
            <span style={{ color: "var(--fg-3)" }}>{datasetId}.</span>{column}
          </h1>
          {stats?.data_type && (
            <span className="t-micro px-1.5 py-0.5 border border-line font-mono" style={{ color: "var(--fg-2)" }}>
              {stats.data_type}
            </span>
          )}
          {stats?.position != null && (
            <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>pos:{stats.position}</span>
          )}
          {!loadingHistory && <VerdictBadge verdict={worstVerdict} />}
          {!loadingHistory && dqtScore !== null && (
            <div className="flex items-center gap-1.5" style={{ borderLeft: "1px solid var(--line)", paddingLeft: 12 }}>
              <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>DQT</span>
              <span className="font-mono" style={{
                fontSize: 18, fontWeight: 300,
                color: dqtScore >= 80 ? "var(--pass)" : dqtScore >= 50 ? "var(--warn)" : "var(--fail)",
                fontFamily: "var(--font-jetbrains-mono)",
              }}>
                {dqtScore}
              </span>
            </div>
          )}
          {stats?.total_count != null && (
            <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>
              {stats.total_count.toLocaleString()} rows
            </span>
          )}
          <button
            onClick={handleRefreshStats}
            disabled={refreshing}
            className="flex items-center gap-1 t-micro border border-line px-2 py-1 hover:border-accent transition-colors disabled:opacity-40"
            style={{ color: "var(--fg-2)", cursor: "pointer" }}
          >
            <RefreshCw size={11} className={refreshing ? "animate-spin" : ""} />
            {refreshing ? "Profiling..." : "Refresh profile"}
          </button>
          {loadingHistory && <Loader2 size={14} className="animate-spin" style={{ color: "var(--fg-3)" }} />}
        </div>

        {/* Two-column grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 380px", gap: 16, alignItems: "start" }}>
          {/* LEFT COLUMN */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {!loadingHistory && (
              <TimeSeriesPanel history={history} schemaHistory={schemaHistory} />
            )}
            {stats && (
              <CompletenessPanel stats={stats} />
            )}
            {stats && stats.kind === "numeric" && (
              <DistributionPanel stats={stats} />
            )}
            {stats && (
              <TopValuesPanel stats={stats} />
            )}
            {!loadingHistory && history.length > 0 && (
              <SeasonalityPanel history={history} />
            )}
          </div>

          {/* RIGHT SIDEBAR */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Summary stats */}
            {stats && <StatsSidebarPanel stats={stats} history={history} />}
            {/* Active checks */}
            <ActiveChecksPanel
              checks={checks}
              latestByDetector={latestByDetector}
              onDelete={id => setChecks(prev => prev.filter(c => c.id !== id))}
              onShowSuggest={() => setShowSuggest(v => !v)}
              showSuggest={showSuggest}
              datasetId={datasetId}
              column={column}
              onCheckAdded={c => setChecks(prev => [...prev, c as ColumnCheck])}
              onCheckDeleted={id => setChecks(prev => prev.filter(c => c.id !== id))}
            />
            <SchemaPanel stats={stats} schemaHistory={schemaHistory} loadingStats={loadingStats} />
            <LineagePanel datasetId={datasetId} column={column} />
            <IncidentsPanel incidents={incidents} />
          </div>
        </div>
      </div>
    </div>
  );
}
```

Note: `StatsSidebarPanel` and `ActiveChecksPanel` are defined inline in page.tsx (not separate files) since they depend on types from the page.

- [ ] **Step 2: Define `StatsSidebarPanel` inline in page.tsx**

Replaces the old `StatCell` grid. Shows 8 cells from warehouse stats + WoW/MoM from CheckRun history:

```tsx
function StatsSidebarPanel({ stats, history }: { stats: ColStats; history: RunPoint[] }) {
  // WoW / MoM still derived from check run history
  const DAY = 86_400_000;
  const now = Date.now();
  const valid = [...history].filter(r => r.score !== null).sort(
    (a, b) => new Date(b.ran_at).getTime() - new Date(a.ran_at).getTime()
  );
  function closestTo(target: number) {
    return valid.sort((a, b) =>
      Math.abs(new Date(a.ran_at).getTime() - target) - Math.abs(new Date(b.ran_at).getTime() - target)
    )[0];
  }
  const latest = valid[0];
  const prev7 = closestTo(now - 7 * DAY);
  const wow = latest && prev7 && latest.id !== prev7.id && latest.score !== null && prev7.score !== null
    ? latest.score - prev7.score : null;
  const prev30 = closestTo(now - 30 * DAY);
  const mom = latest && prev30 && latest.id !== prev30.id && latest.score !== null && prev30.score !== null
    ? latest.score - prev30.score : null;

  function fmt(v: number | null, digits = 3): string {
    if (v === null) return "--";
    return v.toLocaleString(undefined, { maximumFractionDigits: digits });
  }
  function fmtDelta(d: number | null): string {
    if (d === null) return "--";
    const sign = d > 0 ? "+" : "";
    return `${sign}${(d * 100).toFixed(2)}pp`;
  }
  function cv(): string {
    if (stats.p_mean === null || stats.p_stddev === null || stats.p_mean === 0) return "--";
    return `${((stats.p_stddev / Math.abs(stats.p_mean)) * 100).toFixed(1)}%`;
  }

  const cells = [
    { label: "Min", value: fmt(stats.p_min) },
    { label: "Max", value: fmt(stats.p_max) },
    { label: "Mean", value: fmt(stats.p_mean) },
    { label: "Median", value: fmt(stats.p50) },
    { label: "Std Dev", value: fmt(stats.p_stddev) },
    { label: "Volatility", value: cv() },
    { label: "WoW", value: fmtDelta(wow), color: wow !== null && wow > 0.001 ? "var(--fail)" : wow !== null && wow < -0.001 ? "var(--pass)" : undefined },
    { label: "MoM", value: fmtDelta(mom), color: mom !== null && mom > 0.001 ? "var(--fail)" : mom !== null && mom < -0.001 ? "var(--pass)" : undefined },
  ];

  return (
    <div className="border border-line">
      <div className="px-3 py-2 border-b border-line">
        <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Summary Stats</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0, background: "var(--line)" }}>
        {cells.map(({ label, value, color }) => (
          <div key={label} className="px-3 py-2.5" style={{ background: "var(--bg-1)" }}>
            <p className="t-micro mb-1" style={{ color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.06em" }}>{label}</p>
            <p className="font-mono" style={{ fontSize: 14, fontWeight: 300, color: color ?? "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)" }}>{value}</p>
          </div>
        ))}
      </div>
      <div className="px-3 py-1.5 border-t border-line flex gap-3">
        {stats.total_count != null && (
          <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>
            {stats.total_count.toLocaleString()} total
          </span>
        )}
        {stats.null_count != null && stats.total_count != null && stats.total_count > 0 && (
          <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>
            {((stats.null_count / stats.total_count) * 100).toFixed(1)}% null
          </span>
        )}
        {stats.distinct_count != null && (
          <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>
            {stats.distinct_count.toLocaleString()} distinct
          </span>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Define `ActiveChecksPanel` inline in page.tsx**

```tsx
function ActiveChecksPanel({
  checks, latestByDetector, onDelete, onShowSuggest, showSuggest,
  datasetId, column, onCheckAdded, onCheckDeleted,
}: {
  checks: ColumnCheck[];
  latestByDetector: Map<string, RunPoint>;
  onDelete: (id: string) => void;
  onShowSuggest: () => void;
  showSuggest: boolean;
  datasetId: string;
  column: string;
  onCheckAdded: (c: ColumnCheck) => void;
  onCheckDeleted: (id: string) => void;
}) {
  async function handleDeleteCheck(id: string) {
    await fetch(`/api/v1/checks/${encodeURIComponent(id)}`, { method: "DELETE" });
    onDelete(id);
  }

  return (
    <div className="border border-line" style={{ background: "var(--bg-1)" }}>
      <div className="px-3 py-2 border-b border-line flex items-center justify-between">
        <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Active Checks</span>
        <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>{checks.length}</span>
      </div>
      {checks.length === 0 ? (
        <div className="px-3 py-3 t-small" style={{ color: "var(--fg-3)" }}>No checks defined.</div>
      ) : (
        <table className="w-full" style={{ borderCollapse: "collapse" }}>
          <tbody>
            {checks.map(chk => {
              const run = latestByDetector.get(chk.detector_slug);
              const verdict = run?.verdict ?? "pending";
              return (
                <tr key={chk.id} className="border-b border-line last:border-0"
                  style={{ background: verdict === "fail" ? "var(--fail-bg)" : undefined }}>
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-1.5">
                      <div style={{ width: 5, height: 5, background: DETECTOR_CAT[chk.detector_slug] ? CAT_COLOR[DETECTOR_CAT[chk.detector_slug]] : "var(--fg-3)", flexShrink: 0 }} />
                      <span className="t-micro font-mono" style={{ color: "var(--fg-0)" }}>{chk.detector_slug}</span>
                    </div>
                  </td>
                  <td className="px-2 py-2"><VerdictBadge verdict={verdict} /></td>
                  <td className="px-2 py-2 text-right">
                    <button onClick={() => handleDeleteCheck(chk.id)} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--fg-3)" }}>
                      <Trash2 size={11} strokeWidth={1.5} />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      <button onClick={onShowSuggest} className="w-full px-3 py-2 flex items-center gap-1.5 border-t border-line hover:opacity-80 transition-colors" style={{ background: "none", border: "none", borderTop: "1px solid var(--line)", cursor: "pointer" }}>
        <Plus size={11} strokeWidth={1.6} style={{ color: "var(--accent)" }} />
        <span className="t-micro" style={{ color: "var(--fg-2)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Add checks</span>
      </button>
      {showSuggest && (
        <div className="border-t border-line">
          <SuggestPanel
            datasetId={datasetId}
            column={column}
            existingChecks={checks}
            onCheckAdded={onCheckAdded}
            onCheckDeleted={onCheckDeleted}
          />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run `pnpm build` from apps/web to check for TS errors**

```bash
cd apps/web
pnpm build 2>&1 | tail -30
```

Fix any type errors before committing.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/app/\(app\)/datasets/\[id\]/\[column\]/page.tsx
git commit -m "feat(ui): column profile two-column layout + header + sidebar stats"
```

---

## Task 8: Frontend — TimeSeriesPanel

**Files:**
- Create: `apps/web/src/components/column-profile/time-series-panel.tsx`

Features:
- Time window tabs: 7d / 14d / 30d / 90d
- Expected band (rolling p25-p75 over the full history window, shaded)
- Outlier annotations: points >2σ from mean get a small σ label
- Schema change vertical lines from `schemaHistory`
- Y-axis auto-scoped to p2-p98 of all scores (not raw min/max)

- [ ] **Step 1: Create the file**

```tsx
"use client"

import { useState, useMemo } from "react"

interface RunPoint {
  id: number
  detector: string
  score: number | null
  verdict: string | null
  ran_at: string
}

interface SchemaEntry {
  id: number
  data_type: string | null
  nullable: boolean | null
  position: number | null
  recorded_at: string
}

const DETECTOR_CAT: Record<string, string> = {
  completeness: "completeness", null_fraction: "completeness", volume: "completeness",
  uniqueness: "validity", validity: "validity",
  ks_pvalue: "drift", wasserstein_1: "drift", psi: "drift",
  mad_outlier_fraction: "outliers", double_mad_outlier_fraction: "outliers",
  stl_residual_zscore: "timeseries", prophet_anomaly: "timeseries",
}
const CAT_COLOR: Record<string, string> = {
  completeness: "var(--pass)", validity: "var(--accent)",
  drift: "var(--warn)", outliers: "var(--fail)",
  timeseries: "#9b8fff", custom: "var(--fg-3)",
}
function detectorColor(slug: string): string {
  return CAT_COLOR[DETECTOR_CAT[slug] ?? "custom"] ?? "var(--fg-3)"
}

const WINDOWS = [
  { label: "7d", days: 7 },
  { label: "14d", days: 14 },
  { label: "30d", days: 30 },
  { label: "90d", days: 90 },
]

export function TimeSeriesPanel({ history, schemaHistory }: {
  history: RunPoint[]
  schemaHistory: SchemaEntry[]
}) {
  const [windowDays, setWindowDays] = useState(30)

  const cutoff = Date.now() - windowDays * 86_400_000

  const windowedRuns = useMemo(
    () => history.filter(r => r.score !== null && new Date(r.ran_at).getTime() >= cutoff),
    [history, cutoff]
  )

  if (windowedRuns.length === 0) {
    return (
      <div className="border border-line" style={{ background: "var(--bg-1)" }}>
        <div className="px-4 py-2.5 border-b border-line flex items-center justify-between">
          <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Check Score History</span>
          <TabBar windowDays={windowDays} setWindowDays={setWindowDays} />
        </div>
        <div className="px-4 py-6 t-small text-center" style={{ color: "var(--fg-3)" }}>No check runs in selected window.</div>
      </div>
    )
  }

  const W = 700, H = 180, PL = 44, PB = 24, PT = 12, PR = 12
  const IW = W - PL - PR
  const IH = H - PT - PB

  const allScores = windowedRuns.map(r => r.score as number).sort((a, b) => a - b)
  const p2 = allScores[Math.floor(allScores.length * 0.02)] ?? allScores[0]
  const p98 = allScores[Math.floor(allScores.length * 0.98)] ?? allScores[allScores.length - 1]
  const yMin = Math.max(0, p2 * 0.9)
  const yMax = Math.min(1, p98 * 1.1 || 0.01)

  // Global p25-p75 for expected band
  const p25 = allScores[Math.floor(allScores.length * 0.25)] ?? allScores[0]
  const p75 = allScores[Math.floor(allScores.length * 0.75)] ?? allScores[allScores.length - 1]

  const times = windowedRuns.map(r => new Date(r.ran_at).getTime())
  const tMin = Math.min(...times)
  const tMax = Math.max(...times)
  const tRange = Math.max(tMax - tMin, 1)

  const xp = (t: number) => PL + ((t - tMin) / tRange) * IW
  const yp = (s: number) => PT + (1 - (Math.min(Math.max(s, yMin), yMax) - yMin) / (yMax - yMin)) * IH

  // Expected band (horizontal shaded region)
  const bandY1 = yp(p75)
  const bandY2 = yp(p25)

  // Per-detector lines
  const byDet: Record<string, RunPoint[]> = {}
  for (const r of windowedRuns) {
    if (!byDet[r.detector]) byDet[r.detector] = []
    byDet[r.detector].push(r)
  }

  const paths = Object.entries(byDet).map(([det, pts]) => {
    const sorted = [...pts].sort((a, b) => new Date(a.ran_at).getTime() - new Date(b.ran_at).getTime())
    const d = sorted.map((p, i) =>
      `${i === 0 ? "M" : "L"} ${xp(new Date(p.ran_at).getTime()).toFixed(1)} ${yp(p.score as number).toFixed(1)}`
    ).join(" ")
    return { det, d, color: detectorColor(det) }
  })

  // Outlier detection: points >2σ from mean
  const mean = allScores.reduce((a, b) => a + b, 0) / allScores.length
  const std = Math.sqrt(allScores.reduce((s, v) => s + (v - mean) ** 2, 0) / allScores.length)
  const outlierRuns = windowedRuns.filter(r => Math.abs((r.score as number) - mean) > 2 * std)

  // Schema change lines (filter to window)
  const schemaChanges = schemaHistory.filter(e => new Date(e.recorded_at).getTime() >= cutoff)

  // Y grid values
  const yStep = (yMax - yMin) / 4
  const yGridVals = [0, 1, 2, 3, 4].map(i => yMin + i * yStep)

  // X ticks
  const xTicks = [
    { t: tMin, anchor: "start" as const },
    { t: (tMin + tMax) / 2, anchor: "middle" as const },
    { t: tMax, anchor: "end" as const },
  ]
  function fmtDate(ts: number) {
    const d = new Date(ts)
    return `${d.getMonth() + 1}/${d.getDate()}`
  }
  function fmtPct(v: number) {
    return `${(v * 100).toFixed(0)}%`
  }

  const detectors = Object.keys(byDet)

  return (
    <div className="border border-line" style={{ background: "var(--bg-1)" }}>
      <div className="px-4 py-2.5 border-b border-line flex items-center justify-between">
        <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
          Check Score History
        </span>
        <TabBar windowDays={windowDays} setWindowDays={setWindowDays} />
      </div>
      <div className="px-4 py-3">
        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: H, display: "block" }}>
          {/* Expected band */}
          <rect
            x={PL} y={bandY1} width={IW} height={Math.max(0, bandY2 - bandY1)}
            fill="var(--accent)" opacity={0.07}
          />
          {/* Y grid */}
          {yGridVals.map(v => (
            <g key={v}>
              <line x1={PL} y1={yp(v)} x2={W - PR} y2={yp(v)} stroke="var(--line)" strokeWidth={1} opacity={0.6} />
              <text x={PL - 4} y={yp(v) + 3.5} textAnchor="end" fontSize={9} fill="var(--fg-3)" fontFamily="var(--font-jetbrains-mono)">
                {fmtPct(v)}
              </text>
            </g>
          ))}
          {/* Axes */}
          <line x1={PL} y1={PT} x2={PL} y2={H - PB} stroke="var(--line)" strokeWidth={1} />
          <line x1={PL} y1={H - PB} x2={W - PR} y2={H - PB} stroke="var(--line)" strokeWidth={1} />
          {/* Schema change vertical lines */}
          {schemaChanges.map(e => {
            const tx = xp(new Date(e.recorded_at).getTime())
            return (
              <line key={e.id} x1={tx} y1={PT} x2={tx} y2={H - PB}
                stroke="var(--warn)" strokeWidth={1} strokeDasharray="3,3" opacity={0.7} />
            )
          })}
          {/* Detector lines */}
          {paths.map(({ det, d, color }) => (
            <path key={det} d={d} fill="none" stroke={color} strokeWidth={1.5} opacity={0.85} strokeLinejoin="round" />
          ))}
          {/* Dots */}
          {windowedRuns.map((r, i) => (
            <circle key={i}
              cx={xp(new Date(r.ran_at).getTime())} cy={yp(r.score as number)}
              r={2} fill={detectorColor(r.detector)} opacity={0.75} />
          ))}
          {/* Outlier annotations */}
          {outlierRuns.map((r, i) => {
            const cx = xp(new Date(r.ran_at).getTime())
            const cy = yp(r.score as number)
            const sigma = std > 0 ? ((r.score as number) - mean) / std : 0
            return (
              <g key={i}>
                <circle cx={cx} cy={cy} r={3.5} fill="none" stroke="var(--fail)" strokeWidth={1} opacity={0.8} />
                <text x={cx} y={cy - 6} textAnchor="middle" fontSize={8} fill="var(--fail)" fontFamily="var(--font-jetbrains-mono)" opacity={0.8}>
                  {sigma > 0 ? "+" : ""}{sigma.toFixed(1)}σ
                </text>
              </g>
            )
          })}
          {/* X labels */}
          {xTicks.map(({ t, anchor }) => (
            <text key={t} x={xp(t)} y={H - 6} textAnchor={anchor} fontSize={9} fill="var(--fg-3)" fontFamily="var(--font-jetbrains-mono)">
              {fmtDate(t)}
            </text>
          ))}
        </svg>
        {/* Legend */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5">
          {detectors.map(det => (
            <div key={det} className="flex items-center gap-1">
              <div style={{ width: 12, height: 2, background: detectorColor(det) }} />
              <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>{det}</span>
            </div>
          ))}
          <div className="flex items-center gap-1">
            <div style={{ width: 12, height: 8, background: "var(--accent)", opacity: 0.15 }} />
            <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>expected band (p25-p75)</span>
          </div>
          {schemaChanges.length > 0 && (
            <div className="flex items-center gap-1">
              <div style={{ width: 12, height: 0, borderTop: "1px dashed var(--warn)" }} />
              <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>schema change</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function TabBar({ windowDays, setWindowDays }: { windowDays: number; setWindowDays: (d: number) => void }) {
  return (
    <div className="flex gap-0">
      {WINDOWS.map(w => (
        <button
          key={w.days}
          onClick={() => setWindowDays(w.days)}
          className="t-micro px-2 py-1 transition-colors"
          style={{
            color: windowDays === w.days ? "var(--accent)" : "var(--fg-3)",
            background: windowDays === w.days ? "var(--accent-bg)" : "transparent",
            border: "1px solid var(--line)",
            borderRight: "none",
            cursor: "pointer",
            fontFamily: "var(--font-jetbrains-mono)",
          }}
        >
          {w.label}
        </button>
      ))}
      <button
        onClick={() => {}}
        style={{ width: 1, border: "1px solid var(--line)", background: "var(--line)" }}
      />
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/src/components/column-profile/time-series-panel.tsx
git commit -m "feat(ui): TimeSeriesPanel with time window tabs, expected band, outlier annotations"
```

---

## Task 9: Frontend — CompletenessPanel

**Files:**
- Create: `apps/web/src/components/column-profile/completeness-panel.tsx`

Shows a horizontal bar for null rate + a 6-cell completeness grid.

- [ ] **Step 1: Create the file**

```tsx
"use client"

interface ColStats {
  total_count: number | null
  null_count: number | null
  zero_count: number | null
  empty_count: number | null
  distinct_count: number | null
  p_min: number | null
  p_max: number | null
}

function pct(n: number | null, total: number | null): string {
  if (n === null || !total) return "--"
  return `${((n / total) * 100).toFixed(2)}%`
}
function pctNum(n: number | null, total: number | null): number {
  if (n === null || !total) return 0
  return n / total
}

export function CompletenessPanel({ stats }: { stats: ColStats }) {
  const total = stats.total_count ?? 0
  const nullRate = pctNum(stats.null_count, total)
  const validRate = total > 0 ? 1 - nullRate : 0

  const cells = [
    { label: "Null", value: pct(stats.null_count, total), color: nullRate > 0.05 ? "var(--fail)" : nullRate > 0.005 ? "var(--warn)" : "var(--pass)" },
    { label: "Zero", value: pct(stats.zero_count, total), color: "var(--fg-1)" },
    { label: "Empty string", value: pct(stats.empty_count, total), color: "var(--fg-1)" },
    { label: "Distinct", value: stats.distinct_count?.toLocaleString() ?? "--", color: "var(--fg-1)" },
    { label: "Valid", value: pct(total - (stats.null_count ?? 0), total), color: validRate >= 0.99 ? "var(--pass)" : validRate >= 0.95 ? "var(--warn)" : "var(--fail)" },
    { label: "Total rows", value: total.toLocaleString(), color: "var(--fg-1)" },
  ]

  return (
    <div className="border border-line" style={{ background: "var(--bg-1)" }}>
      <div className="px-4 py-2.5 border-b border-line">
        <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Completeness & Validity</span>
      </div>
      {/* Null bar */}
      <div className="px-4 py-3 border-b border-line">
        <div className="flex items-center gap-2 mb-1">
          <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>null rate</span>
          <span className="t-micro font-mono" style={{ color: nullRate > 0.05 ? "var(--fail)" : nullRate > 0.005 ? "var(--warn)" : "var(--pass)" }}>
            {pct(stats.null_count, total)}
          </span>
        </div>
        <div style={{ height: 6, background: "var(--bg-0)", border: "1px solid var(--line)", overflow: "hidden" }}>
          <div style={{
            width: `${nullRate * 100}%`, height: "100%",
            background: nullRate > 0.05 ? "var(--fail)" : nullRate > 0.005 ? "var(--warn)" : "var(--pass)",
            transition: "width 0.4s ease",
          }} />
        </div>
      </div>
      {/* 6-cell grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 0, background: "var(--line)" }}>
        {cells.map(({ label, value, color }) => (
          <div key={label} className="px-4 py-3" style={{ background: "var(--bg-1)" }}>
            <p className="t-micro mb-1" style={{ color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.06em" }}>{label}</p>
            <p className="font-mono" style={{ fontSize: 13, fontWeight: 400, color, fontFamily: "var(--font-jetbrains-mono)" }}>{value}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/src/components/column-profile/completeness-panel.tsx
git commit -m "feat(ui): CompletenessPanel with null bar and 6-cell grid"
```

---

## Task 10: Frontend — DistributionPanel + PercentileTable

**Files:**
- Create: `apps/web/src/components/column-profile/distribution-panel.tsx`

Side-by-side: left is histogram SVG, right is percentile table p5-p99.

- [ ] **Step 1: Create the file**

```tsx
"use client"

interface Bucket {
  lower: number
  upper: number
  count: number
  is_outlier: boolean
}

interface ColStats {
  kind: string
  histogram: Bucket[]
  p5: number | null; p10: number | null; p25: number | null
  p50: number | null; p75: number | null; p90: number | null
  p95: number | null; p99: number | null
  p_mean: number | null; p_stddev: number | null
}

function fmtNum(v: number | null, sig = 4): string {
  if (v === null) return "--"
  const abs = Math.abs(v)
  if (abs >= 1_000_000) return `${(v / 1_000_000).toFixed(2)}M`
  if (abs >= 1_000) return `${(v / 1_000).toFixed(1)}k`
  if (abs < 0.0001 && abs > 0) return v.toExponential(2)
  return v.toPrecision(sig).replace(/\.?0+$/, "")
}

export function DistributionPanel({ stats }: { stats: ColStats }) {
  const buckets = stats.histogram ?? []
  if (buckets.length === 0) return null

  const maxCount = Math.max(...buckets.map(b => b.count), 1)
  const W = 300, H = 120, PL = 4, PB = 16, PT = 4, PR = 4
  const IW = W - PL - PR
  const IH = H - PT - PB
  const bw = IW / buckets.length

  const percentiles = [
    { label: "p5", value: stats.p5 },
    { label: "p10", value: stats.p10 },
    { label: "p25", value: stats.p25 },
    { label: "p50", value: stats.p50 },
    { label: "p75", value: stats.p75 },
    { label: "p90", value: stats.p90 },
    { label: "p95", value: stats.p95 },
    { label: "p99", value: stats.p99 },
  ]

  return (
    <div className="border border-line" style={{ background: "var(--bg-1)" }}>
      <div className="px-4 py-2.5 border-b border-line">
        <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Distribution</span>
      </div>
      <div className="flex" style={{ gap: 0 }}>
        {/* Histogram */}
        <div className="flex-1 px-4 py-3 border-r border-line">
          <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: H, display: "block" }}>
            {buckets.map((b, i) => {
              const bh = (b.count / maxCount) * IH
              const x = PL + i * bw
              const y = PT + IH - bh
              const color = b.is_outlier ? "var(--fail)" : "var(--accent)"
              return (
                <rect key={i} x={x + 0.5} y={y} width={Math.max(bw - 1, 1)} height={bh}
                  fill={color} opacity={b.is_outlier ? 0.4 : 0.55} />
              )
            })}
            {/* Mean line */}
            {stats.p_mean !== null && (() => {
              const lo = buckets[0].lower
              const hi = buckets[buckets.length - 1].upper
              const mx = PL + ((stats.p_mean - lo) / (hi - lo)) * IW
              return (
                <line x1={mx} y1={PT} x2={mx} y2={H - PB}
                  stroke="var(--fg-1)" strokeWidth={1} strokeDasharray="3,2" opacity={0.5} />
              )
            })()}
            {/* X labels */}
            <text x={PL} y={H - 2} textAnchor="start" fontSize={8} fill="var(--fg-3)" fontFamily="var(--font-jetbrains-mono)">
              {fmtNum(buckets[0].lower)}
            </text>
            <text x={W - PR} y={H - 2} textAnchor="end" fontSize={8} fill="var(--fg-3)" fontFamily="var(--font-jetbrains-mono)">
              {fmtNum(buckets[buckets.length - 1].upper)}
            </text>
          </svg>
          <div className="mt-1 flex items-center gap-3">
            <div className="flex items-center gap-1">
              <div style={{ width: 8, height: 8, background: "var(--accent)", opacity: 0.55 }} />
              <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>in range</span>
            </div>
            <div className="flex items-center gap-1">
              <div style={{ width: 8, height: 8, background: "var(--fail)", opacity: 0.4 }} />
              <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>outlier buckets</span>
            </div>
          </div>
        </div>
        {/* Percentile table */}
        <div className="py-3" style={{ minWidth: 140 }}>
          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <tbody>
              {percentiles.map(({ label, value }) => (
                <tr key={label} className="border-b border-line last:border-0">
                  <td className="px-3 py-1 t-micro font-mono" style={{ color: "var(--fg-3)" }}>{label}</td>
                  <td className="px-3 py-1 t-micro font-mono text-right" style={{ color: "var(--fg-0)" }}>{fmtNum(value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/src/components/column-profile/distribution-panel.tsx
git commit -m "feat(ui): DistributionPanel with histogram and percentile table"
```

---

## Task 11: Frontend — TopValuesPanel

**Files:**
- Create: `apps/web/src/components/column-profile/top-values-panel.tsx`

Three-tab view: Bucketed (histogram bars), Categorical (top-N list with bar), Pattern (prefix grouping).

- [ ] **Step 1: Create the file**

```tsx
"use client"

import { useState, useMemo } from "react"

interface TopValue {
  value: string
  count: number
  pct: number
}

interface ColStats {
  kind: string
  top_values: TopValue[]
  total_count: number | null
}

type TabKey = "values" | "patterns"

export function TopValuesPanel({ stats }: { stats: ColStats }) {
  const [tab, setTab] = useState<TabKey>("values")

  const topValues = stats.top_values ?? []
  if (topValues.length === 0) return null

  // Pattern grouping: strip trailing digits to find common prefixes
  const patterns = useMemo(() => {
    const groups: Record<string, { count: number; examples: string[] }> = {}
    for (const tv of topValues) {
      const pattern = tv.value.replace(/\d+/g, "N").replace(/[a-f0-9]{8,}/gi, "<hex>")
      if (!groups[pattern]) groups[pattern] = { count: 0, examples: [] }
      groups[pattern].count += tv.count
      if (groups[pattern].examples.length < 2) groups[pattern].examples.push(tv.value)
    }
    return Object.entries(groups).sort((a, b) => b[1].count - a[1].count).slice(0, 10)
  }, [topValues])

  const maxCount = Math.max(...topValues.map(v => v.count), 1)
  const total = stats.total_count ?? 0

  return (
    <div className="border border-line" style={{ background: "var(--bg-1)" }}>
      <div className="px-4 py-2 border-b border-line flex items-center justify-between">
        <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Top Values</span>
        <div className="flex">
          {(["values", "patterns"] as TabKey[]).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className="t-micro px-3 py-1 transition-colors"
              style={{
                color: tab === t ? "var(--accent)" : "var(--fg-3)",
                borderBottom: tab === t ? "1px solid var(--accent)" : "1px solid transparent",
                background: "transparent", cursor: "pointer",
              }}>
              {t === "values" ? "Values" : "Patterns"}
            </button>
          ))}
        </div>
      </div>
      {tab === "values" && (
        <div>
          {topValues.slice(0, 15).map(tv => (
            <div key={tv.value} className="flex items-center gap-2 px-4 py-1.5 border-b border-line last:border-0">
              <span className="t-micro font-mono flex-shrink-0" style={{ color: "var(--fg-0)", minWidth: 140, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {tv.value}
              </span>
              <div className="flex-1" style={{ background: "var(--bg-0)", height: 4, borderRadius: 2, overflow: "hidden" }}>
                <div style={{ width: `${(tv.count / maxCount) * 100}%`, height: "100%", background: "var(--accent)", opacity: 0.6 }} />
              </div>
              <span className="t-micro font-mono flex-shrink-0" style={{ color: "var(--fg-3)", minWidth: 48, textAlign: "right" }}>
                {total > 0 ? `${(tv.pct * 100).toFixed(1)}%` : tv.count.toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      )}
      {tab === "patterns" && (
        <div>
          {patterns.map(([pattern, { count, examples }]) => (
            <div key={pattern} className="flex items-center gap-2 px-4 py-1.5 border-b border-line last:border-0">
              <div className="flex-1 min-w-0">
                <span className="t-micro font-mono" style={{ color: "var(--fg-0)" }}>{pattern}</span>
                <span className="t-micro font-mono ml-2" style={{ color: "var(--fg-3)" }}>e.g. {examples.join(", ")}</span>
              </div>
              <span className="t-micro font-mono flex-shrink-0" style={{ color: "var(--fg-3)" }}>
                {count.toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/src/components/column-profile/top-values-panel.tsx
git commit -m "feat(ui): TopValuesPanel with values and patterns tabs"
```

---

## Task 12: Frontend — SchemaPanel

**Files:**
- Create: `apps/web/src/components/column-profile/schema-panel.tsx`

Shows current schema (type, nullable, position) + version history timeline.

- [ ] **Step 1: Create the file**

```tsx
"use client"

interface ColStats {
  data_type: string | null
  nullable: boolean | null
  position: number | null
  computed_at: string
}

interface SchemaEntry {
  id: number
  data_type: string | null
  nullable: boolean | null
  position: number | null
  recorded_at: string
}

function fmtTs(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
}

export function SchemaPanel({ stats, schemaHistory, loadingStats }: {
  stats: ColStats | null
  schemaHistory: SchemaEntry[]
  loadingStats: boolean
}) {
  if (loadingStats && !stats) {
    return (
      <div className="border border-line" style={{ background: "var(--bg-1)" }}>
        <div className="px-3 py-2.5 border-b border-line">
          <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Schema</span>
        </div>
        <div className="px-3 py-3 t-small" style={{ color: "var(--fg-3)" }}>Loading...</div>
      </div>
    )
  }

  return (
    <div className="border border-line" style={{ background: "var(--bg-1)" }}>
      <div className="px-3 py-2.5 border-b border-line">
        <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Schema</span>
      </div>
      {/* Current schema */}
      <div className="px-3 py-2 border-b border-line flex flex-wrap gap-3">
        {stats?.data_type && (
          <div>
            <span className="t-micro" style={{ color: "var(--fg-3)" }}>type </span>
            <span className="t-micro font-mono" style={{ color: "var(--fg-0)" }}>{stats.data_type}</span>
          </div>
        )}
        {stats?.nullable != null && (
          <div>
            <span className="t-micro" style={{ color: "var(--fg-3)" }}>nullable </span>
            <span className="t-micro font-mono" style={{ color: stats.nullable ? "var(--warn)" : "var(--pass)" }}>
              {stats.nullable ? "yes" : "no"}
            </span>
          </div>
        )}
        {stats?.position != null && (
          <div>
            <span className="t-micro" style={{ color: "var(--fg-3)" }}>position </span>
            <span className="t-micro font-mono" style={{ color: "var(--fg-0)" }}>{stats.position}</span>
          </div>
        )}
      </div>
      {/* Version history */}
      {schemaHistory.length > 0 && (
        <div className="px-3 py-2">
          <p className="t-micro mb-1.5" style={{ color: "var(--fg-3)", letterSpacing: "0.06em", textTransform: "uppercase" }}>Version history</p>
          <div className="space-y-0">
            {schemaHistory.map((e, i) => (
              <div key={e.id} className="flex items-start gap-2 py-1.5 border-b border-line last:border-0">
                <div className="flex-shrink-0 mt-1" style={{ width: 6, height: 6, borderRadius: 3, background: i === schemaHistory.length - 1 ? "var(--accent)" : "var(--fg-3)" }} />
                <div className="flex-1 min-w-0">
                  <span className="t-micro font-mono" style={{ color: "var(--fg-0)" }}>{e.data_type ?? "unknown"}</span>
                  {e.nullable != null && (
                    <span className="t-micro font-mono ml-2" style={{ color: "var(--fg-3)" }}>
                      {e.nullable ? "nullable" : "not null"}
                    </span>
                  )}
                </div>
                <span className="t-micro font-mono flex-shrink-0" style={{ color: "var(--fg-3)" }}>
                  {fmtTs(e.recorded_at)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
      {schemaHistory.length === 0 && stats && (
        <div className="px-3 py-2 t-micro" style={{ color: "var(--fg-3)" }}>No schema changes recorded.</div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/src/components/column-profile/schema-panel.tsx
git commit -m "feat(ui): SchemaPanel with current schema + version history timeline"
```

---

## Task 13: Frontend — LineagePanel

**Files:**
- Create: `apps/web/src/components/column-profile/lineage-panel.tsx`

Shows upstream and downstream nodes from the lineage graph. Empty state when no data.

- [ ] **Step 1: Create the file**

```tsx
"use client"

import { useEffect, useState } from "react"

interface LineageNode {
  id: string
  kind: string
  label: string
  dataset: string
  column: string
}

interface LineageEdge {
  id: string
  source: string
  target: string
  kind: string
  confidence: number
}

interface LineageGraph {
  nodes: LineageNode[]
  edges: LineageEdge[]
  root: string | null
}

export function LineagePanel({ datasetId, column }: { datasetId: string; column: string }) {
  const [graph, setGraph] = useState<LineageGraph | null>(null)
  const [loading, setLoading] = useState(true)

  const nodeId = `${datasetId}.${column}`

  useEffect(() => {
    fetch(`/api/v1/lineage/graph?node=${encodeURIComponent(nodeId)}&direction=both&depth=2`)
      .then(r => r.ok ? r.json() : null)
      .then(setGraph)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [nodeId])

  const upstream = graph?.nodes.filter(n =>
    n.id !== nodeId && graph.edges.some(e => e.target === nodeId && e.source === n.id)
  ) ?? []
  const downstream = graph?.nodes.filter(n =>
    n.id !== nodeId && graph.edges.some(e => e.source === nodeId && e.target === n.id)
  ) ?? []

  const hasData = upstream.length > 0 || downstream.length > 0

  return (
    <div className="border border-line" style={{ background: "var(--bg-1)" }}>
      <div className="px-3 py-2.5 border-b border-line">
        <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Lineage</span>
      </div>
      {loading && (
        <div className="px-3 py-3 t-small" style={{ color: "var(--fg-3)" }}>Loading...</div>
      )}
      {!loading && !hasData && (
        <div className="px-3 py-3 t-small" style={{ color: "var(--fg-3)" }}>
          No lineage configured.{" "}
          <a href="/lineage" className="hover:opacity-80" style={{ color: "var(--accent)" }}>Set up lineage →</a>
        </div>
      )}
      {!loading && hasData && (
        <div className="py-2">
          {upstream.length > 0 && (
            <div className="px-3 pb-2 border-b border-line">
              <p className="t-micro mb-1" style={{ color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Upstream</p>
              {upstream.map(n => (
                <div key={n.id} className="flex items-center gap-2 py-1">
                  <div style={{ width: 5, height: 5, background: "var(--fg-3)", flexShrink: 0 }} />
                  <span className="t-micro font-mono" style={{ color: "var(--fg-0)" }}>{n.label || n.id}</span>
                </div>
              ))}
            </div>
          )}
          {downstream.length > 0 && (
            <div className="px-3 pt-2">
              <p className="t-micro mb-1" style={{ color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Downstream</p>
              {downstream.map(n => (
                <div key={n.id} className="flex items-center gap-2 py-1">
                  <div style={{ width: 5, height: 5, background: "var(--accent)", flexShrink: 0 }} />
                  <span className="t-micro font-mono" style={{ color: "var(--fg-0)" }}>{n.label || n.id}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/src/components/column-profile/lineage-panel.tsx
git commit -m "feat(ui): LineagePanel with upstream/downstream nodes and empty state"
```

---

## Task 14: Frontend — IncidentsPanel + SeasonalityPanel

**Files:**
- Create: `apps/web/src/components/column-profile/incidents-panel.tsx`
- Create: `apps/web/src/components/column-profile/seasonality-panel.tsx`

### IncidentsPanel

Shows recent incidents for this column.

```tsx
"use client"

interface ColIncident {
  id: number
  detector_slug: string
  severity: string
  message: string
  status: string
  opened_at: string
  resolved_at: string | null
}

const SEV_COLOR: Record<string, string> = {
  critical: "var(--fail)", high: "var(--fail)",
  medium: "var(--warn)", low: "var(--fg-3)",
}

export function IncidentsPanel({ incidents }: { incidents: ColIncident[] }) {
  return (
    <div className="border border-line" style={{ background: "var(--bg-1)" }}>
      <div className="px-3 py-2.5 border-b border-line flex items-center justify-between">
        <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Recent Incidents</span>
        {incidents.length > 0 && (
          <span className="t-micro font-mono" style={{ color: "var(--fail)" }}>{incidents.filter(i => i.status === "open").length} open</span>
        )}
      </div>
      {incidents.length === 0 ? (
        <div className="px-3 py-3 t-small" style={{ color: "var(--pass)" }}>No incidents.</div>
      ) : (
        <div>
          {incidents.slice(0, 5).map(inc => (
            <div key={inc.id} className="px-3 py-2 border-b border-line last:border-0">
              <div className="flex items-center gap-2 mb-0.5">
                <div style={{ width: 5, height: 5, background: SEV_COLOR[inc.severity] ?? "var(--fg-3)", flexShrink: 0 }} />
                <span className="t-micro font-mono" style={{ color: "var(--fg-0)" }}>{inc.detector_slug}</span>
                <span className="t-micro font-mono ml-auto" style={{ color: inc.status === "open" ? "var(--fail)" : "var(--fg-3)" }}>{inc.status}</span>
              </div>
              <p className="t-micro" style={{ color: "var(--fg-2)", paddingLeft: 13 }}>{inc.message}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

### SeasonalityPanel

Computes from CheckRun history: average check score per day-of-week.

```tsx
"use client"

import { useMemo } from "react"

interface RunPoint {
  id: number
  detector: string
  score: number | null
  verdict: string | null
  ran_at: string
}

const DOW_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

export function SeasonalityPanel({ history }: { history: RunPoint[] }) {
  const dowData = useMemo(() => {
    const buckets: number[][] = Array.from({ length: 7 }, () => [])
    for (const r of history) {
      if (r.score === null) continue
      const dow = new Date(r.ran_at).getDay()
      buckets[dow].push(r.score)
    }
    return buckets.map((scores, dow) => ({
      dow,
      label: DOW_LABELS[dow],
      mean: scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : null,
      count: scores.length,
    }))
  }, [history])

  const hasData = dowData.some(d => d.mean !== null)
  if (!hasData) return null

  const maxMean = Math.max(...dowData.map(d => d.mean ?? 0), 0.01)
  const H = 80

  return (
    <div className="border border-line" style={{ background: "var(--bg-1)" }}>
      <div className="px-4 py-2.5 border-b border-line">
        <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Seasonality (by day of week)</span>
      </div>
      <div className="px-4 py-3">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 4, height: H }}>
          {dowData.map(({ label, mean, count }) => {
            const barH = mean !== null ? (mean / maxMean) * (H - 20) : 0
            const color = mean === null ? "var(--bg-0)"
              : mean > 0.05 ? "var(--fail)"
              : mean > 0.005 ? "var(--warn)"
              : "var(--pass)"
            return (
              <div key={label} style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "flex-end", height: H }}>
                <span className="t-micro font-mono mb-1" style={{ color: "var(--fg-2)", fontSize: 9 }}>
                  {mean !== null ? `${(mean * 100).toFixed(1)}%` : "--"}
                </span>
                <div style={{ width: "100%", height: barH, background: color, opacity: 0.7, minHeight: mean !== null ? 2 : 0 }} />
                <span className="t-micro font-mono mt-1" style={{ color: "var(--fg-3)", fontSize: 9 }}>{label}</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 1: Create both files as shown above**

- [ ] **Step 2: Commit**

```bash
git add apps/web/src/components/column-profile/incidents-panel.tsx apps/web/src/components/column-profile/seasonality-panel.tsx
git commit -m "feat(ui): IncidentsPanel and SeasonalityPanel"
```

---

## Task 15: Build check, integration, and cleanup

**Files:**
- Modify: `apps/web/src/app/(app)/datasets/[id]/[column]/page.tsx` (fix any remaining issues)

- [ ] **Step 1: Run pnpm build and fix all errors**

```bash
cd apps/web
pnpm build 2>&1 | grep -E "Error|error|warning" | head -40
```

Fix each TypeScript/lint error. Common patterns to watch for:
- Missing imports (`Trash2`, `Plus` from lucide-react)
- Duplicate type definitions (consolidate `RunPoint`, `ColumnCheck` interfaces)
- `ColStats` interface mismatch between page.tsx and panel components — each panel defines its own minimal interface, which is correct

- [ ] **Step 2: Verify all panels render with empty data gracefully**

Each panel should handle `null`/empty states without crashing:
- `TimeSeriesPanel`: shows "No check runs in selected window"
- `CompletenessPanel`: shows `--` for all cells
- `DistributionPanel`: returns `null` if no histogram
- `TopValuesPanel`: returns `null` if no top_values
- `LineagePanel`: shows "No lineage configured"
- `IncidentsPanel`: shows "No incidents"
- `SeasonalityPanel`: returns `null` if no data

- [ ] **Step 3: Remove the old unused `CheckTimeSeries` and `computeStats` functions from page.tsx**

These were replaced by `TimeSeriesPanel` and `StatsSidebarPanel`.

- [ ] **Step 4: Final commit**

```bash
git add -p   # stage only the relevant changes
git commit -m "feat(ui): column profile redesign — two-column layout, all panels"
```

---

## Summary of API surface added

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/datasets/{id}/columns/{col}/stats` | GET | Returns cached warehouse stats; computes if missing |
| `/datasets/{id}/columns/{col}/refresh-stats` | POST | Force recompute from warehouse |
| `/datasets/{id}/columns/{col}/schema-history` | GET | Schema change changelog |
| `/datasets/{id}/columns/{col}/incidents` | GET | Recent incidents for this column |

## Summary of new components

| Component | File | Mounted in |
|-----------|------|------------|
| TimeSeriesPanel | column-profile/time-series-panel.tsx | Left column |
| CompletenessPanel | column-profile/completeness-panel.tsx | Left column |
| DistributionPanel | column-profile/distribution-panel.tsx | Left column |
| TopValuesPanel | column-profile/top-values-panel.tsx | Left column |
| SeasonalityPanel | column-profile/seasonality-panel.tsx | Left column |
| StatsSidebarPanel | page.tsx (inline) | Right sidebar |
| ActiveChecksPanel | page.tsx (inline) | Right sidebar |
| SchemaPanel | column-profile/schema-panel.tsx | Right sidebar |
| LineagePanel | column-profile/lineage-panel.tsx | Right sidebar |
| IncidentsPanel | column-profile/incidents-panel.tsx | Right sidebar |
