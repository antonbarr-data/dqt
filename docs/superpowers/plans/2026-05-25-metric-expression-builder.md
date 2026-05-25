# Metric Expression Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to define computed metric formulas (simple aggregations, ratios, filtered expressions, or raw SQL) when creating or editing a metric, with live warehouse preview.

**Architecture:** Expression fields are stored on `MetricDefinition`; the visual builder constructs a runnable SQL aggregate expression (`expr_sql`) client-side using CASE WHEN for filters, avoiding any adapter protocol changes. A lightweight `MetricRun` table persists evaluation results. Two endpoints handle expression work: `POST /metrics/evaluate-expression` (preview, no save) and `POST /metrics/{fqn}/evaluate` (run + persist).

**Tech Stack:** Python/FastAPI/SQLAlchemy async (backend), React/Next.js App Router `"use client"` (frontend), existing `adapter.aggregate()` for warehouse execution, Recharts (chart), Tailwind + CSS variables for styling.

---

## File Map

| File | Change |
|---|---|
| `apps/server/src/dqt_server/models/core.py` | Add 6 expression columns to `MetricDefinition`; add `MetricRun` model |
| `apps/server/src/dqt_server/main.py` | Add 6 DDL `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` migrations |
| `apps/server/src/dqt_server/api/v1/insights.py` | Add evaluate endpoints; extend MetricCreate / MetricPatch / MetricBatchItem; include expression fields in `get_metric` response |
| `apps/web/src/app/(app)/metrics/[fqn]/expression-builder.tsx` | **New** — ExpressionBuilder client component |
| `apps/web/src/app/(app)/metrics/page.tsx` | Add expression section to "New metric" inline form |
| `apps/web/src/app/(app)/metrics/[fqn]/metric-profile-panel.tsx` | Show expression in view mode; add ExpressionBuilder in edit mode |

---

## Task 1: MetricDefinition expression fields + MetricRun model + DDL

**Files:**
- Modify: `apps/server/src/dqt_server/models/core.py:122-144`
- Modify: `apps/server/src/dqt_server/main.py:56-75`

- [ ] **Step 1: Write the failing test**

```python
# apps/server/tests/test_metric_expression_model.py
import pytest
from dqt_server.models.core import MetricDefinition, MetricRun


def test_metric_definition_has_expression_fields():
    m = MetricDefinition(
        fqn="test.default.orders.take_rate",
        display_name="Take Rate",
        kind="ratio",
        dataset="orders",
        expr_type="ratio",
        expr_sql="(SUM(fee_usd)) / NULLIF((SUM(amount_usd)), 0)",
        numerator_sql="SUM(fee_usd)",
        denominator_sql="SUM(amount_usd)",
        filter_sql="status = 'completed'",
        time_column="date",
    )
    assert m.expr_type == "ratio"
    assert "NULLIF" in m.expr_sql
    assert m.time_column == "date"


def test_metric_run_model():
    from datetime import datetime, timezone
    r = MetricRun(fqn="test.default.orders.take_rate", value=0.0342)
    assert r.fqn == "test.default.orders.take_rate"
    assert r.value == pytest.approx(0.0342)
```

- [ ] **Step 2: Run test to verify it fails**

```
cd apps/server
uv run pytest tests/test_metric_expression_model.py -v
```
Expected: FAIL with `TypeError` (unexpected keyword arguments)

- [ ] **Step 3: Add expression fields to MetricDefinition and add MetricRun**

In `apps/server/src/dqt_server/models/core.py`, add after the `lineage` field (line ~140) and before `created_at`:

```python
    # Expression fields — define how this metric's value is computed
    expr_type: Mapped[str | None] = mapped_column(String, nullable=True)          # simple|ratio|custom
    expr_sql: Mapped[str | None] = mapped_column(Text, nullable=True)             # full runnable aggregate expression
    numerator_sql: Mapped[str | None] = mapped_column(Text, nullable=True)        # UI reconstruction for ratio mode
    denominator_sql: Mapped[str | None] = mapped_column(Text, nullable=True)      # UI reconstruction for ratio mode
    filter_sql: Mapped[str | None] = mapped_column(Text, nullable=True)           # WHERE clause (for UI display; baked into expr_sql)
    time_column: Mapped[str | None] = mapped_column(String, nullable=True)        # date/time column for time-window context
```

Add `Text` to the existing import line:
```python
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
```

Add new `MetricRun` class after `MetricDefinition`:
```python
class MetricRun(Base):
    """One row per metric evaluation result; enables historical value tracking."""
    __tablename__ = "metric_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fqn: Mapped[str] = mapped_column(String, nullable=False, index=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    ran_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
```

- [ ] **Step 4: Add DDL migrations in main.py**

In `apps/server/src/dqt_server/main.py`, add these lines inside the `for stmt in [...]` block (after the existing `lineage JSONB` entry, before the closing `]:`):

```python
            "ALTER TABLE metric_definitions ADD COLUMN IF NOT EXISTS expr_type VARCHAR",
            "ALTER TABLE metric_definitions ADD COLUMN IF NOT EXISTS expr_sql TEXT",
            "ALTER TABLE metric_definitions ADD COLUMN IF NOT EXISTS numerator_sql TEXT",
            "ALTER TABLE metric_definitions ADD COLUMN IF NOT EXISTS denominator_sql TEXT",
            "ALTER TABLE metric_definitions ADD COLUMN IF NOT EXISTS filter_sql TEXT",
            "ALTER TABLE metric_definitions ADD COLUMN IF NOT EXISTS time_column VARCHAR",
```

(`MetricRun` table is created by `Base.metadata.create_all` automatically — no DDL ALTER needed.)

- [ ] **Step 5: Run test to verify it passes**

```
cd apps/server
uv run pytest tests/test_metric_expression_model.py -v
```
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add apps/server/src/dqt_server/models/core.py apps/server/src/dqt_server/main.py apps/server/tests/test_metric_expression_model.py
git commit -m "feat(metrics): add expression fields to MetricDefinition + MetricRun table"
```

---

## Task 2: Expression evaluation endpoints

**Files:**
- Modify: `apps/server/src/dqt_server/api/v1/insights.py`

Two endpoints:
- `POST /api/v1/metrics/evaluate-expression` — preview: run an expression against a dataset, return value without saving. Used by the ExpressionBuilder preview button before a metric exists.
- `POST /api/v1/metrics/{fqn:path}/evaluate` — run the saved expression, store result in `metric_runs`.

Both use `adapter.aggregate(schema, table, [AggExpr("result", expr_sql)])` from the existing warehouse adapter, executed in a thread pool (adapter is sync).

- [ ] **Step 1: Write failing tests**

```python
# apps/server/tests/test_metric_evaluate.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from dqt_server.main import app


@pytest.mark.asyncio
async def test_evaluate_expression_missing_source(async_client: AsyncClient):
    resp = await async_client.post("/api/v1/metrics/evaluate-expression", json={
        "dataset": "nonexistent_table",
        "source_id": "nonexistent_source",
        "expr_sql": "SUM(amount_usd)",
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_evaluate_metric_no_expression(async_client: AsyncClient, seeded_metric):
    # seeded_metric has no expr_sql set
    resp = await async_client.post(f"/api/v1/metrics/{seeded_metric}/evaluate")
    assert resp.status_code == 400
    assert "no expression" in resp.json()["detail"].lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd apps/server
uv run pytest tests/test_metric_evaluate.py -v
```
Expected: FAIL with `404` (routes don't exist yet)

- [ ] **Step 3: Add evaluate-expression endpoint**

Add these imports at the top of `insights.py` (they're already available in check_runner):

```python
import asyncio
```

(already imported — verify it's present; if not, add it)

Add this Pydantic model and endpoint in `insights.py`, immediately before the `@router.delete("/metrics/{fqn:path}")` route:

```python
class ExpressionPreviewBody(PydanticBaseModel):
    dataset: str
    source_id: str
    expr_sql: str


@router.post("/metrics/evaluate-expression")
async def evaluate_expression(body: ExpressionPreviewBody, db: AsyncSession = Depends(get_db)) -> dict:
    """Run an aggregate expression against a warehouse dataset and return the scalar result.
    Does not require an existing metric. Used for expression preview during metric creation."""
    from dqt_server.models.core import Dataset, Source
    from dqt_server.check_runner import _make_adapter, _default_schema_for_source
    from dqt.adapters._protocol import AggExpr

    d = await db.get(Dataset, body.dataset)
    if d is None:
        raise HTTPException(404, detail=f"Dataset '{body.dataset}' not found")
    s = await db.get(Source, body.source_id)
    if s is None:
        raise HTTPException(404, detail=f"Source '{body.source_id}' not found")

    loop = asyncio.get_event_loop()

    def _run() -> dict:
        adapter = _make_adapter(s)
        if s.engine == "bigquery" and "." in body.dataset:
            schema, table = body.dataset.split(".", 1)
        else:
            schema = _default_schema_for_source(s) or d.schema_name or "public"
            table = body.dataset
        try:
            result = adapter.aggregate(schema, table, [AggExpr("result", body.expr_sql)])
            val = result.get("result")
            return {"value": float(val) if val is not None else None, "error": None}
        except Exception as exc:
            return {"value": None, "error": str(exc)}

    return await loop.run_in_executor(None, _run)
```

- [ ] **Step 4: Add evaluate-and-store endpoint**

Add this after the `evaluate-expression` endpoint (still before `delete`):

```python
@router.post("/metrics/{fqn:path}/evaluate")
async def evaluate_metric(fqn: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Run the saved expression for an existing metric, store the result in metric_runs."""
    from dqt_server.models.core import Dataset, Source, MetricRun
    from dqt_server.check_runner import _make_adapter, _default_schema_for_source
    from dqt.adapters._protocol import AggExpr

    row = await db.get(MetricDefinition, fqn)
    if row is None:
        raise HTTPException(404, detail=f"Metric '{fqn}' not found")
    if not row.expr_sql or not row.source_id:
        raise HTTPException(400, detail="Metric has no expression or source configured")

    d = await db.get(Dataset, row.dataset)
    s = await db.get(Source, row.source_id)
    if d is None or s is None:
        raise HTTPException(400, detail="Dataset or source not found for this metric")

    loop = asyncio.get_event_loop()

    def _run() -> float | None:
        adapter = _make_adapter(s)
        if s.engine == "bigquery" and "." in row.dataset:
            schema, table = row.dataset.split(".", 1)
        else:
            schema = _default_schema_for_source(s) or d.schema_name or "public"
            table = row.dataset
        result = adapter.aggregate(schema, table, [AggExpr("result", row.expr_sql)])
        val = result.get("result")
        return float(val) if val is not None else None

    value = await loop.run_in_executor(None, _run)
    ran_at = datetime.now(timezone.utc)
    db.add(MetricRun(fqn=fqn, value=value, ran_at=ran_at))
    await db.commit()
    global _registry
    _registry = None
    return {"value": value, "ran_at": ran_at.isoformat()}
```

- [ ] **Step 5: Run tests to verify they pass**

```
cd apps/server
uv run pytest tests/test_metric_evaluate.py -v
```
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add apps/server/src/dqt_server/api/v1/insights.py apps/server/tests/test_metric_evaluate.py
git commit -m "feat(metrics): evaluate-expression preview endpoint + evaluate-and-store endpoint"
```

---

## Task 3: Update MetricCreate / MetricPatch / MetricBatchItem + get_metric response

**Files:**
- Modify: `apps/server/src/dqt_server/api/v1/insights.py`

Add the 6 expression fields to every create/patch/batch schema, persist them in the corresponding endpoints, and include them in the `get_metric` response so the frontend can reconstruct the builder state.

- [ ] **Step 1: Write the failing test**

```python
# apps/server/tests/test_metric_expression_crud.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_metric_with_expression(async_client: AsyncClient):
    resp = await async_client.post("/api/v1/metrics", json={
        "display_name": "Take Rate",
        "kind": "ratio",
        "dataset": "gigler_transactions",
        "expr_type": "ratio",
        "expr_sql": "(SUM(platform_fee_usd)) / NULLIF((SUM(amount_usd)), 0)",
        "numerator_sql": "SUM(platform_fee_usd)",
        "denominator_sql": "SUM(amount_usd)",
        "filter_sql": "status = 'completed'",
        "time_column": "date",
    })
    assert resp.status_code == 201
    fqn = resp.json()["fqn"]

    detail = await async_client.get(f"/api/v1/metrics/{fqn}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["expr_type"] == "ratio"
    assert "NULLIF" in body["expr_sql"]
    assert body["numerator_sql"] == "SUM(platform_fee_usd)"
    assert body["filter_sql"] == "status = 'completed'"
    assert body["time_column"] == "date"


@pytest.mark.asyncio
async def test_patch_metric_expression(async_client: AsyncClient, seeded_metric):
    resp = await async_client.patch(f"/api/v1/metrics/{seeded_metric}", json={
        "expr_type": "simple",
        "expr_sql": "COUNT(*)",
    })
    assert resp.status_code == 200
    detail = await async_client.get(f"/api/v1/metrics/{seeded_metric}")
    assert detail.json()["expr_sql"] == "COUNT(*)"
```

- [ ] **Step 2: Run test to verify it fails**

```
cd apps/server
uv run pytest tests/test_metric_expression_crud.py -v
```
Expected: FAIL (extra fields are rejected or silently dropped)

- [ ] **Step 3: Extend MetricCreate**

In `insights.py`, update the `MetricCreate` class:

```python
class MetricCreate(PydanticBaseModel):
    display_name: str
    kind: str = "ratio"
    dataset: str
    description: str = ""
    owners: list[str] = []
    tags: list[str] = []
    source_id: str | None = None
    expr_type: str | None = None
    expr_sql: str | None = None
    numerator_sql: str | None = None
    denominator_sql: str | None = None
    filter_sql: str | None = None
    time_column: str | None = None
```

Update the `create_metric` endpoint body to persist expression fields:

```python
    m = MetricDefinition(
        fqn=fqn,
        display_name=body.display_name,
        kind=body.kind,
        dataset=body.dataset,
        description=body.description,
        owners=body.owners,
        tags=body.tags,
        source_id=body.source_id,
        expr_type=body.expr_type,
        expr_sql=body.expr_sql,
        numerator_sql=body.numerator_sql,
        denominator_sql=body.denominator_sql,
        filter_sql=body.filter_sql,
        time_column=body.time_column,
        created_at=datetime.now(timezone.utc),
    )
```

- [ ] **Step 4: Extend MetricPatch**

```python
class MetricPatch(PydanticBaseModel):
    kind: str | None = None
    description: str | None = None
    owners: list[str] | None = None
    tags: list[str] | None = None
    warn_threshold: float | None = None
    fail_threshold: float | None = None
    grain: str | None = None
    additivity: str | None = None
    good_direction: str | None = None
    refresh_cadence: str | None = None
    lineage: list | None = None
    expr_type: str | None = None
    expr_sql: str | None = None
    numerator_sql: str | None = None
    denominator_sql: str | None = None
    filter_sql: str | None = None
    time_column: str | None = None
```

Add patch handling in `patch_metric` endpoint, after the existing `if body.lineage is not None:` block:

```python
    if body.expr_type is not None:
        m.expr_type = body.expr_type or None
    if body.expr_sql is not None:
        m.expr_sql = body.expr_sql or None
    if body.numerator_sql is not None:
        m.numerator_sql = body.numerator_sql or None
    if body.denominator_sql is not None:
        m.denominator_sql = body.denominator_sql or None
    if body.filter_sql is not None:
        m.filter_sql = body.filter_sql or None
    if body.time_column is not None:
        m.time_column = body.time_column or None
```

- [ ] **Step 5: Extend MetricBatchItem**

```python
class MetricBatchItem(PydanticBaseModel):
    display_name: str
    kind: str = "ratio"
    dataset: str
    description: str = ""
    owners: list[str] = []
    tags: list[str] = []
    source_id: str | None = None
    column_name: str | None = None
    grain: str | None = None
    additivity: str | None = None
    good_direction: str | None = None
    refresh_cadence: str | None = None
    expr_type: str | None = None
    expr_sql: str | None = None
    numerator_sql: str | None = None
    denominator_sql: str | None = None
    filter_sql: str | None = None
    time_column: str | None = None
```

Update `create_metrics_batch` to persist expression fields in `db.add(MetricDefinition(...))`:

```python
            db.add(MetricDefinition(
                fqn=fqn,
                display_name=item.display_name,
                kind=item.kind,
                dataset=item.dataset,
                description=item.description,
                owners=item.owners,
                tags=item.tags,
                source_id=item.source_id,
                column_name=item.column_name,
                grain=item.grain,
                additivity=item.additivity,
                good_direction=item.good_direction,
                refresh_cadence=item.refresh_cadence,
                expr_type=item.expr_type,
                expr_sql=item.expr_sql,
                numerator_sql=item.numerator_sql,
                denominator_sql=item.denominator_sql,
                filter_sql=item.filter_sql,
                time_column=item.time_column,
                created_at=datetime.now(timezone.utc),
            ))
```

- [ ] **Step 6: Extend get_metric response**

In `get_metric`, add expression fields to the returned dict:

```python
    return {
        ...existing fields...,
        "expr_type": row.expr_type,
        "expr_sql": row.expr_sql,
        "numerator_sql": row.numerator_sql,
        "denominator_sql": row.denominator_sql,
        "filter_sql": row.filter_sql,
        "time_column": row.time_column,
    }
```

- [ ] **Step 7: Run test to verify it passes**

```
cd apps/server
uv run pytest tests/test_metric_expression_crud.py -v
```
Expected: PASS (2 tests)

- [ ] **Step 8: Commit**

```bash
git add apps/server/src/dqt_server/api/v1/insights.py apps/server/tests/test_metric_expression_crud.py
git commit -m "feat(metrics): expression fields in create/patch/batch APIs and get_metric response"
```

---

## Task 4: ExpressionBuilder React component

**Files:**
- Create: `apps/web/src/app/(app)/metrics/[fqn]/expression-builder.tsx`

This component renders 3 tabs (Simple / Ratio / Custom SQL). It fetches columns from the dataset, generates `expr_sql` client-side, and previews the result against the warehouse.

SQL generation rules (implemented client-side in TypeScript):

| Mode | Filter | Output |
|---|---|---|
| Simple SUM/AVG/MIN/MAX, no filter | — | `SUM(col)` |
| Simple SUM/AVG/MIN/MAX, with filter | `f` | `SUM(CASE WHEN f THEN col END)` |
| Simple COUNT, no filter | — | `COUNT(*)` |
| Simple COUNT, with filter | `f` | `COUNT(CASE WHEN f THEN 1 END)` |
| Simple COUNT DISTINCT, no filter | — | `COUNT(DISTINCT col)` |
| Simple COUNT DISTINCT, with filter | `f` | `COUNT(DISTINCT CASE WHEN f THEN col END)` |
| Ratio | any | `(num_expr) / NULLIF((den_expr), 0)` |
| Custom | — | user input verbatim |

- [ ] **Step 1: Create the file**

Create `apps/web/src/app/(app)/metrics/[fqn]/expression-builder.tsx`:

```tsx
"use client";

import { useState, useEffect, useCallback } from "react";
import { Loader2 } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface ExpressionDef {
  type: "simple" | "ratio" | "custom";
  agg: string;
  column: string;
  numeratorAgg: string;
  numeratorCol: string;
  denominatorAgg: string;
  denominatorCol: string;
  filterSql: string;
  customSql: string;
  exprSql: string;
}

export function emptyExpression(): ExpressionDef {
  return {
    type: "simple",
    agg: "sum",
    column: "",
    numeratorAgg: "sum",
    numeratorCol: "",
    denominatorAgg: "count",
    denominatorCol: "*",
    filterSql: "",
    customSql: "",
    exprSql: "",
  };
}

const AGGS = ["sum", "count", "count_distinct", "avg", "min", "max"] as const;

function buildSimpleExpr(agg: string, col: string, filter: string): string {
  if (!col && agg !== "count") return "";
  const c = col || "*";
  if (!filter) {
    if (agg === "count") return "COUNT(*)";
    if (agg === "count_distinct") return `COUNT(DISTINCT ${c})`;
    return `${agg.toUpperCase()}(${c})`;
  }
  if (agg === "count") return `COUNT(CASE WHEN ${filter} THEN 1 END)`;
  if (agg === "count_distinct") return `COUNT(DISTINCT CASE WHEN ${filter} THEN ${c} END)`;
  return `${agg.toUpperCase()}(CASE WHEN ${filter} THEN ${c} END)`;
}

function buildExprSql(def: ExpressionDef): string {
  if (def.type === "custom") return def.customSql.trim();
  if (def.type === "simple") return buildSimpleExpr(def.agg, def.column, def.filterSql);
  if (def.type === "ratio") {
    const num = buildSimpleExpr(def.numeratorAgg, def.numeratorCol, def.filterSql);
    const den = buildSimpleExpr(def.denominatorAgg, def.denominatorCol, def.filterSql);
    if (!num || !den) return "";
    return `(${num}) / NULLIF((${den}), 0)`;
  }
  return "";
}

interface Props {
  dataset: string;
  sourceId: string | null;
  value: ExpressionDef;
  onChange: (v: ExpressionDef) => void;
}

export function ExpressionBuilder({ dataset, sourceId, value, onChange }: Props) {
  const [columns, setColumns] = useState<string[]>([]);
  const [previewing, setPreviewing] = useState(false);
  const [previewResult, setPreviewResult] = useState<{ value: number | null; error: string | null } | null>(null);

  useEffect(() => {
    if (!dataset) return;
    fetch(`${API}/api/v1/datasets/${encodeURIComponent(dataset)}/columns`)
      .then((r) => (r.ok ? r.json() : []))
      .then((cols: { name: string }[]) => setColumns(cols.map((c) => c.name)))
      .catch(() => {});
  }, [dataset]);

  const update = useCallback(
    (patch: Partial<ExpressionDef>) => {
      const next = { ...value, ...patch };
      next.exprSql = buildExprSql(next);
      onChange(next);
      setPreviewResult(null);
    },
    [value, onChange]
  );

  async function preview() {
    const sql = buildExprSql(value);
    if (!sql || !dataset || !sourceId) return;
    setPreviewing(true);
    setPreviewResult(null);
    try {
      const res = await fetch(`${API}/api/v1/metrics/evaluate-expression`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dataset, source_id: sourceId, expr_sql: sql }),
      });
      setPreviewResult(await res.json());
    } catch {
      setPreviewResult({ value: null, error: "Network error" });
    } finally {
      setPreviewing(false);
    }
  }

  const generatedSql = buildExprSql(value);
  const canPreview = !!generatedSql && !!dataset && !!sourceId;

  const tabStyle = (active: boolean) => ({
    color: active ? "var(--accent)" : "var(--fg-2)",
    borderBottom: active ? "1px solid var(--accent)" : "1px solid transparent",
    background: "transparent",
  });

  const inputStyle = {
    background: "var(--bg-0)",
    color: "var(--fg-0)",
    outline: "none",
  } as const;

  return (
    <div className="border border-line" style={{ background: "var(--bg-1)" }}>
      {/* Tabs */}
      <div className="flex border-b border-line">
        {(["simple", "ratio", "custom"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => update({ type: tab })}
            className="px-4 py-2 t-small capitalize"
            style={tabStyle(value.type === tab)}
          >
            {tab === "count_distinct" ? "Count Distinct" : tab}
          </button>
        ))}
      </div>

      <div className="p-4 space-y-3">
        {/* Simple mode */}
        {value.type === "simple" && (
          <div className="flex items-end gap-3 flex-wrap">
            <div>
              <label className="t-micro block mb-1" style={{ color: "var(--fg-2)" }}>Aggregation</label>
              <select
                value={value.agg}
                onChange={(e) => update({ agg: e.target.value })}
                className="px-2 py-1.5 t-small border border-line"
                style={inputStyle}
              >
                {AGGS.map((a) => (
                  <option key={a} value={a}>{a === "count_distinct" ? "COUNT DISTINCT" : a.toUpperCase()}</option>
                ))}
              </select>
            </div>
            {value.agg !== "count" && (
              <div>
                <label className="t-micro block mb-1" style={{ color: "var(--fg-2)" }}>Column</label>
                <select
                  value={value.column}
                  onChange={(e) => update({ column: e.target.value })}
                  className="px-2 py-1.5 t-small border border-line font-mono"
                  style={{ ...inputStyle, minWidth: 160 }}
                >
                  <option value="">— pick column —</option>
                  {columns.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
            )}
            <div className="flex-1 min-w-48">
              <label className="t-micro block mb-1" style={{ color: "var(--fg-2)" }}>Filter (WHERE)</label>
              <input
                value={value.filterSql}
                onChange={(e) => update({ filterSql: e.target.value })}
                placeholder="e.g. status = 'completed'"
                className="w-full px-2 py-1.5 t-small border border-line font-mono"
                style={inputStyle}
              />
            </div>
          </div>
        )}

        {/* Ratio mode */}
        {value.type === "ratio" && (
          <div className="space-y-3">
            <div>
              <p className="t-micro mb-2" style={{ color: "var(--fg-2)" }}>Numerator</p>
              <div className="flex items-center gap-3 flex-wrap">
                <select
                  value={value.numeratorAgg}
                  onChange={(e) => update({ numeratorAgg: e.target.value })}
                  className="px-2 py-1.5 t-small border border-line"
                  style={inputStyle}
                >
                  {AGGS.map((a) => (
                    <option key={a} value={a}>{a === "count_distinct" ? "COUNT DISTINCT" : a.toUpperCase()}</option>
                  ))}
                </select>
                {value.numeratorAgg !== "count" && (
                  <select
                    value={value.numeratorCol}
                    onChange={(e) => update({ numeratorCol: e.target.value })}
                    className="px-2 py-1.5 t-small border border-line font-mono"
                    style={{ ...inputStyle, minWidth: 160 }}
                  >
                    <option value="">— pick column —</option>
                    {columns.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                )}
              </div>
            </div>
            <div>
              <p className="t-micro mb-2" style={{ color: "var(--fg-2)" }}>Denominator</p>
              <div className="flex items-center gap-3 flex-wrap">
                <select
                  value={value.denominatorAgg}
                  onChange={(e) => update({ denominatorAgg: e.target.value })}
                  className="px-2 py-1.5 t-small border border-line"
                  style={inputStyle}
                >
                  {AGGS.map((a) => (
                    <option key={a} value={a}>{a === "count_distinct" ? "COUNT DISTINCT" : a.toUpperCase()}</option>
                  ))}
                </select>
                {value.denominatorAgg !== "count" && (
                  <select
                    value={value.denominatorCol}
                    onChange={(e) => update({ denominatorCol: e.target.value })}
                    className="px-2 py-1.5 t-small border border-line font-mono"
                    style={{ ...inputStyle, minWidth: 160 }}
                  >
                    <option value="">— pick column —</option>
                    {columns.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                )}
              </div>
            </div>
            <div>
              <label className="t-micro block mb-1" style={{ color: "var(--fg-2)" }}>Filter (applied to both numerator and denominator)</label>
              <input
                value={value.filterSql}
                onChange={(e) => update({ filterSql: e.target.value })}
                placeholder="e.g. status = 'completed'"
                className="w-full px-2 py-1.5 t-small border border-line font-mono"
                style={inputStyle}
              />
            </div>
          </div>
        )}

        {/* Custom SQL mode */}
        {value.type === "custom" && (
          <div>
            <label className="t-micro block mb-1" style={{ color: "var(--fg-2)" }}>
              SQL aggregate expression
            </label>
            <p className="t-micro mb-2" style={{ color: "var(--fg-3)" }}>
              Write any aggregate expression. This runs as: SELECT <em>your expression</em> FROM {dataset || "…"}
            </p>
            <textarea
              value={value.customSql}
              onChange={(e) => update({ customSql: e.target.value })}
              rows={3}
              placeholder="e.g. SUM(platform_fee_usd) / NULLIF(SUM(amount_usd), 0)"
              className="w-full px-2 py-1.5 t-small border border-line font-mono resize-none"
              style={inputStyle}
            />
          </div>
        )}

        {/* Generated SQL preview + run button */}
        {generatedSql && (
          <div className="flex items-start gap-3 pt-1">
            <div className="flex-1 min-w-0">
              <p className="t-micro mb-1" style={{ color: "var(--fg-3)" }}>Expression</p>
              <code
                className="block t-micro font-mono px-2 py-1.5 border border-line overflow-x-auto"
                style={{ background: "var(--bg-0)", color: "var(--fg-1)" }}
              >
                SELECT {generatedSql} FROM {dataset || "…"}
              </code>
            </div>
            {canPreview && (
              <div className="flex-shrink-0 pt-5">
                <button
                  onClick={preview}
                  disabled={previewing}
                  className="flex items-center gap-1.5 px-3 py-1.5 t-small border hover:opacity-80 disabled:opacity-40"
                  style={{ color: "var(--accent)", borderColor: "var(--accent)" }}
                >
                  {previewing ? <Loader2 size={11} strokeWidth={2} className="animate-spin" /> : "▶"}
                  Preview
                </button>
              </div>
            )}
          </div>
        )}

        {previewResult && (
          <div
            className="px-3 py-2 t-small font-mono border"
            style={{
              borderColor: previewResult.error ? "var(--fail)" : "var(--pass)",
              color: previewResult.error ? "var(--fail)" : "var(--fg-0)",
              background: previewResult.error ? "rgba(224,123,110,0.06)" : "rgba(100,200,120,0.06)",
            }}
          >
            {previewResult.error
              ? `Error: ${previewResult.error}`
              : `Result: ${previewResult.value != null ? previewResult.value.toLocaleString(undefined, { maximumFractionDigits: 6 }) : "null"}`
            }
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Build to verify TypeScript is clean**

```
cd apps/web
pnpm build
```
Expected: `✓ Compiled successfully`

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/app/\(app\)/metrics/\[fqn\]/expression-builder.tsx
git commit -m "feat(metrics): ExpressionBuilder component with simple/ratio/custom modes and live preview"
```

---

## Task 5: Wire ExpressionBuilder into New Metric form

**Files:**
- Modify: `apps/web/src/app/(app)/metrics/page.tsx`

Add an "Expression (optional)" section below the existing Kind/Description fields in the "New metric" inline form. The section is collapsed by default (user clicks "Add expression" to expand it).

- [ ] **Step 1: Update MetricsPage state and imports**

In `apps/web/src/app/(app)/metrics/page.tsx`, add to the import block:

```typescript
import { ExpressionBuilder, ExpressionDef, emptyExpression } from "./[fqn]/expression-builder";
```

Add state variables after the existing form state (around line 127):

```typescript
  const [formExprOpen, setFormExprOpen] = useState(false);
  const [formExpr, setFormExpr] = useState<ExpressionDef>(emptyExpression());
  const [formSourceId, setFormSourceId] = useState("");
```

- [ ] **Step 2: Update handleSubmit to include expression fields**

In `handleSubmit`, update the POST body:

```typescript
        body: JSON.stringify({
          display_name: formName.trim(),
          kind: formKind,
          dataset: formDataset.trim(),
          description: formDescription.trim(),
          source_id: formSourceId || null,
          ...(formExprOpen && formExpr.exprSql ? {
            expr_type: formExpr.type,
            expr_sql: formExpr.exprSql,
            numerator_sql: formExpr.numeratorSql || null,
            denominator_sql: formExpr.denominatorSql || null,
            filter_sql: formExpr.filterSql || null,
          } : {}),
        }),
```

Also reset expression state on successful create:

```typescript
        setFormExpr(emptyExpression());
        setFormExprOpen(false);
        setFormSourceId("");
```

- [ ] **Step 3: Update the Dataset field to also set sourceId**

The form currently has a plain text input for `formDataset`. We need `source_id` for the ExpressionBuilder preview. Fetch datasets on form open and swap to a dropdown when datasets are available.

Add state: `const [formDatasets, setFormDatasets] = useState<DatasetItem[]>([]);`

Update the `setFormOpen` button handler to also fetch datasets:

```typescript
            onClick={() => {
              setFormOpen((v) => !v);
              setFormError(null);
              if (!formOpen && datasets.length === 0) {
                fetch(`${API}/api/v1/datasets`)
                  .then((r) => r.ok ? r.json() : [])
                  .then((d: DatasetItem[]) => setFormDatasets(d))
                  .catch(() => {});
              }
            }}
```

Replace the Dataset `<input>` with a hybrid: if `formDatasets` is loaded, show a `<select>` that sets both `formDataset` and `formSourceId`; otherwise keep the text input:

```tsx
            {formDatasets.length > 0 ? (
              <select
                value={formDataset}
                onChange={(e) => {
                  setFormDataset(e.target.value);
                  const d = formDatasets.find((x) => x.id === e.target.value);
                  setFormSourceId(d ? (d as DatasetItem & { source_id?: string }).source_id ?? "" : "");
                }}
                className="w-full px-3 py-2 border border-line t-small outline-none"
                style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
              >
                <option value="">— select dataset —</option>
                {formDatasets.map((d) => <option key={d.id} value={d.id}>{d.id}</option>)}
              </select>
            ) : (
              <input
                type="text" value={formDataset} onChange={(e) => setFormDataset(e.target.value)}
                placeholder="e.g. fct_orders"
                className="w-full px-3 py-2 border border-line t-small outline-none"
                style={{ background: "var(--bg-2)", color: "var(--fg-0)" }}
              />
            )}
```

Note: the `DatasetItem` type needs a `source_id` field. Update the interface:

```typescript
interface DatasetItem {
  id: string;
  source: string;
  schema: string;
  source_id?: string;
}
```

(The `/api/v1/datasets` endpoint already returns `source_id` on each dataset row — verify this; if not, the preview simply won't be available but the rest works fine.)

- [ ] **Step 4: Add ExpressionBuilder section to the form**

Inside the `<form>` element, after the `grid grid-cols-2` fields block and before `{formError && ...}`:

```tsx
          {/* Expression section */}
          <div>
            <button
              type="button"
              onClick={() => setFormExprOpen((v) => !v)}
              className="flex items-center gap-1.5 t-micro hover:opacity-80"
              style={{ color: formExprOpen ? "var(--accent)" : "var(--fg-3)" }}
            >
              <span style={{ fontSize: 10, fontFamily: "var(--font-jetbrains-mono)" }}>
                {formExprOpen ? "▾" : "▸"}
              </span>
              Expression {formExprOpen ? "" : "(optional)"}
            </button>
            {formExprOpen && (
              <div className="mt-2">
                <ExpressionBuilder
                  dataset={formDataset}
                  sourceId={formSourceId || null}
                  value={formExpr}
                  onChange={setFormExpr}
                />
              </div>
            )}
          </div>
```

- [ ] **Step 5: Build to verify TypeScript is clean**

```
cd apps/web
pnpm build
```
Expected: `✓ Compiled successfully`

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/app/\(app\)/metrics/page.tsx
git commit -m "feat(metrics): add optional expression builder to New Metric form"
```

---

## Task 6: Wire ExpressionBuilder into MetricProfilePanel

**Files:**
- Modify: `apps/web/src/app/(app)/metrics/[fqn]/metric-profile-panel.tsx`

Show the saved expression in view mode (formatted formula block). Show the ExpressionBuilder in edit mode so the formula can be updated.

- [ ] **Step 1: Extend the Props interface and component state**

In `metric-profile-panel.tsx`, update the `Props` interface:

```typescript
interface Props {
  fqn: string;
  description: string;
  grain: string | null;
  additivity: string | null;
  good_direction: string | null;
  refresh_cadence: string | null;
  lineage: { label: string; kind?: string }[];
  // Expression fields
  source_id: string | null;
  expr_type: string | null;
  expr_sql: string | null;
  numerator_sql: string | null;
  denominator_sql: string | null;
  filter_sql: string | null;
}
```

Add imports:

```typescript
import { ExpressionBuilder, ExpressionDef, emptyExpression } from "./expression-builder";
```

Add expression state inside `MetricProfilePanel`:

```typescript
  function initialExpr(): ExpressionDef {
    const base = emptyExpression();
    if (!initialExprType) return base;
    return {
      ...base,
      type: (initialExprType as ExpressionDef["type"]) ?? "simple",
      customSql: initialExprSql ?? "",
      numeratorAgg: "sum",
      numeratorCol: "",
      denominatorAgg: "count",
      denominatorCol: "*",
      filterSql: initialFilterSql ?? "",
      exprSql: initialExprSql ?? "",
    };
  }
  const [expr, setExpr] = useState<ExpressionDef>(initialExpr);
```

Update the destructured props:

```typescript
export function MetricProfilePanel({
  fqn,
  description: initialDescription,
  grain: initialGrain,
  additivity: initialAdditivity,
  good_direction: initialDirection,
  refresh_cadence: initialCadence,
  lineage: initialLineage,
  source_id: initialSourceId,
  expr_type: initialExprType,
  expr_sql: initialExprSql,
  numerator_sql: initialNumeratorSql,
  denominator_sql: initialDenominatorSql,
  filter_sql: initialFilterSql,
}: Props) {
```

- [ ] **Step 2: Include expression in save()**

In the `save()` function, add expression fields to the PATCH body:

```typescript
      body: JSON.stringify({
        description,
        grain: grain || null,
        additivity: additivity || null,
        good_direction: direction || null,
        refresh_cadence: cadence || null,
        lineage: lineage.map((l) => ({ label: l })),
        expr_type: expr.type || null,
        expr_sql: expr.exprSql || null,
        numerator_sql: expr.numeratorSql || null,
        denominator_sql: expr.denominatorSql || null,
        filter_sql: expr.filterSql || null,
      }),
```

- [ ] **Step 3: Add expression view in non-editing mode**

Inside the component's render, after the description paragraph and before the lineage strip, add:

```tsx
      {/* Expression formula — view mode */}
      {initialExprSql && !editing && (
        <div className="mb-2">
          <p className="t-micro mb-1" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Expression</p>
          <code
            className="block t-micro font-mono px-2 py-1.5 border border-line overflow-x-auto"
            style={{ background: "var(--bg-0)", color: "var(--fg-1)" }}
          >
            SELECT {initialExprSql} FROM {fqn.split(".").at(-2) ?? "…"}
          </code>
        </div>
      )}
```

- [ ] **Step 4: Add ExpressionBuilder inside edit form**

Inside the `{editing && (...)}` block, after the lineage section and before the Save/Cancel buttons:

```tsx
          <div>
            <label className="t-micro block mb-1" style={{ color: "var(--fg-2)" }}>Expression</label>
            <ExpressionBuilder
              dataset={fqn.split(".").at(-2) ?? ""}
              sourceId={initialSourceId}
              value={expr}
              onChange={setExpr}
            />
          </div>
```

- [ ] **Step 5: Pass new props from the parent page**

In `apps/web/src/app/(app)/metrics/[fqn]/page.tsx`, update the `MetricDetail` interface:

```typescript
interface MetricDetail {
  ...existing fields...
  source_id: string | null;
  expr_type: string | null;
  expr_sql: string | null;
  numerator_sql: string | null;
  denominator_sql: string | null;
  filter_sql: string | null;
}
```

Update the `<MetricProfilePanel>` JSX to pass the new props:

```tsx
      <MetricProfilePanel
        fqn={decodedFqn}
        description={metric.description}
        grain={metric.grain}
        additivity={metric.additivity}
        good_direction={metric.good_direction}
        refresh_cadence={metric.refresh_cadence}
        lineage={metric.lineage}
        source_id={metric.source_id}
        expr_type={metric.expr_type}
        expr_sql={metric.expr_sql}
        numerator_sql={metric.numerator_sql}
        denominator_sql={metric.denominator_sql}
        filter_sql={metric.filter_sql}
      />
```

- [ ] **Step 6: Build to verify TypeScript is clean**

```
cd apps/web
pnpm build
```
Expected: `✓ Compiled successfully`

- [ ] **Step 7: Commit**

```bash
git add \
  apps/web/src/app/\(app\)/metrics/\[fqn\]/metric-profile-panel.tsx \
  apps/web/src/app/\(app\)/metrics/\[fqn\]/page.tsx
git commit -m "feat(metrics): show and edit metric expression in MetricProfilePanel"
```

---

## Self-Review

**Spec coverage:**
- ✅ Simple aggregation (SUM/COUNT/AVG/MIN/MAX/COUNT DISTINCT) with column picker
- ✅ Ratio (numerator/denominator) with shared filter
- ✅ Custom SQL expression
- ✅ Filter applied via CASE WHEN — no adapter protocol change required
- ✅ Live preview calls `evaluate-expression` endpoint
- ✅ Expression persists on create (MetricCreate), edit (MetricPatch), bulk import (MetricBatchItem)
- ✅ Expression displayed in view mode on metric detail page
- ✅ Evaluate-and-store endpoint (`POST /metrics/{fqn}/evaluate`) persists to `metric_runs`

**Placeholder scan:** None found — all code blocks are complete.

**Type consistency:** `ExpressionDef.exprSql` is set by `buildExprSql()` in every `update()` call; passed as `expr_sql` to PATCH endpoint. `emptyExpression()` provides a valid default. All prop names consistent across Tasks 4–6.

**Out of scope (intentional):** Scheduled evaluation (triggering `/evaluate` on a cadence), updating the `series` endpoint to serve from `metric_runs`, and time-window filtering via `time_column` — these are follow-on features.
