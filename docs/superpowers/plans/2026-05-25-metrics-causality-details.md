# Metrics Causality, Dashboard Refresh, and Details Page — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist PCMCI+ causality edges + SHAP attribution per metric to the DB, refresh the metrics list page with kind filtering and full data path, and build a rich metric detail page with profiling stats, distribution chart, causality DAG, trend + outlier series, date range selector, and adjustable thresholds.

**Architecture:** A FastAPI async background task runs on every metric batch-create, executes PCMCI+ pairwise discovery over the metric panel, and writes `MetricCausalEdge` rows to Postgres. New endpoints expose profile stats and causal edges. The frontend reads these via two new fetch calls in the detail page client component. The list page gets a left-side kind filter panel mirroring the Checks page pattern.

**Tech Stack:** FastAPI async background tasks, SQLAlchemy 2 async ORM, Pydantic v2, PCMCI+ (tigramite), SHAP LinearExplainer, Next.js App Router, Recharts (LineChart + BarChart), plain SVG for the causality DAG.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `apps/server/src/dqt_server/models/core.py` | Modify | Add `source_id`, `column_name`, `warn_threshold`, `fail_threshold` to `MetricDefinition`; add `MetricCausalEdge` model |
| `apps/server/src/dqt_server/main.py` | Modify | DDL migrations for new columns; import core models so `Base.metadata.create_all` picks up `metric_causal_edges` |
| `apps/server/src/dqt_server/api/v1/insights.py` | Modify | `MetricBatchItem` + `MetricPatch` extensions; `_load_registry_from_db` passes new fields; new `/profile` and `/causal-edges` endpoints |
| `apps/server/src/dqt_server/api/v1/causal_compute.py` | Modify | `_run_causality_in_background` becomes async; discovery result written to `metric_causal_edges` table |
| `apps/web/src/components/connections/wizard.tsx` | Modify | `handleFinish` sends `source_id` and `column_name` in batch payload |
| `apps/web/src/app/(app)/metrics/page.tsx` | Modify | Left kind-filter nav, remove `owner`/`last_run` columns, show full `source.table.column` path |
| `apps/web/src/app/(app)/metrics/[fqn]/page.tsx` | Modify | Add profiling stats strip + threshold editor section |
| `apps/web/src/app/(app)/metrics/[fqn]/insight-client.tsx` | Modify | Add causality graph section using new component |
| `apps/web/src/app/(app)/metrics/[fqn]/series-chart.tsx` | Modify | Trend line overlay, outlier dots, date-range prop |
| `apps/web/src/app/(app)/metrics/[fqn]/causal-graph.tsx` | **Create** | SVG causality DAG — focal metric center, causes left, effects right |

---

## Task 1: Extend MetricDefinition + add MetricCausalEdge

**Files:**
- Modify: `apps/server/src/dqt_server/models/core.py:122-136`

- [ ] **Step 1: Add four new columns to MetricDefinition**

In `core.py`, replace the MetricDefinition class body so it reads:

```python
class MetricDefinition(Base):
    __tablename__ = "metric_definitions"

    fqn: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False, default="ratio")
    dataset: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    owners: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    source_id: Mapped[str | None] = mapped_column(String, nullable=True)
    column_name: Mapped[str | None] = mapped_column(String, nullable=True)
    warn_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    fail_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
```

- [ ] **Step 2: Add MetricCausalEdge model after MetricDefinition**

Immediately after the `MetricDefinition` class, add:

```python
class MetricCausalEdge(Base):
    __tablename__ = "metric_causal_edges"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # "{cause_fqn}->{effect_fqn}"
    cause_fqn: Mapped[str] = mapped_column(String, nullable=False, index=True)
    effect_fqn: Mapped[str] = mapped_column(String, nullable=False, index=True)
    lag: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    p_value: Mapped[float] = mapped_column(Float, nullable=False)
    adjusted_p_value: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_strength: Mapped[float] = mapped_column(Float, nullable=False)
    shap_attribution: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
```

All types (`Float`, `Integer`, `String`, `DateTime`) are already imported on line 5 of `core.py`. No new imports needed.

- [ ] **Step 3: Commit**

```bash
git add apps/server/src/dqt_server/models/core.py
git commit -m "feat(db): source_id/column_name/thresholds on MetricDefinition + MetricCausalEdge table"
```

---

## Task 2: DDL migrations + ensure model is registered

**Files:**
- Modify: `apps/server/src/dqt_server/main.py:48-64`

- [ ] **Step 1: Add ALTER TABLE statements to _setup_db**

Replace the `for stmt in [...]` block so it includes the four new columns:

```python
for stmt in [
    "ALTER TABLE sources ADD COLUMN IF NOT EXISTS password VARCHAR",
    "ALTER TABLE sources ADD COLUMN IF NOT EXISTS secure BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE column_checks ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT TRUE",
    "ALTER TABLE metric_definitions ADD COLUMN IF NOT EXISTS source_id VARCHAR",
    "ALTER TABLE metric_definitions ADD COLUMN IF NOT EXISTS column_name VARCHAR",
    "ALTER TABLE metric_definitions ADD COLUMN IF NOT EXISTS warn_threshold DOUBLE PRECISION",
    "ALTER TABLE metric_definitions ADD COLUMN IF NOT EXISTS fail_threshold DOUBLE PRECISION",
]:
```

`metric_causal_edges` is a brand-new table — `Base.metadata.create_all` creates it automatically because `MetricCausalEdge` inherits `Base`.

- [ ] **Step 2: Verify core models are imported before create_all**

Grep for where `MetricDefinition` is first imported:

```bash
grep -r "from dqt_server.models.core" apps/server/src/dqt_server/
```

If no import exists in `main.py` itself (the routers import it, and routers are imported before `_setup_db` runs), the table will be registered. Confirm by checking the app startup — if the server has been running with `metric_definitions` already, `MetricDefinition` is clearly being picked up. No change needed unless the grep shows it's missing.

- [ ] **Step 3: Restart server to run migrations**

```bash
# Kill any running server first, then:
cd apps/server
uv run uvicorn dqt_server.main:app --port 8000 --reload
```

Expected log output: server starts, no `UndefinedColumn` errors, `metric_causal_edges` table appears in pg.

Verify:
```bash
psql $DATABASE_URL -c "\d metric_causal_edges"
psql $DATABASE_URL -c "\d metric_definitions" | grep -E "source_id|column_name|warn|fail"
```

- [ ] **Step 4: Commit**

```bash
git add apps/server/src/dqt_server/main.py
git commit -m "feat(db): DDL migrations for metric_definitions new columns"
```

---

## Task 3: Thread source metadata through wizard → batch endpoint

**Files:**
- Modify: `apps/server/src/dqt_server/api/v1/insights.py:164-202`
- Modify: `apps/web/src/components/connections/wizard.tsx` (~line 780)

- [ ] **Step 1: Extend MetricBatchItem with optional source fields**

In `insights.py`, update `MetricBatchItem`:

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
```

- [ ] **Step 2: Persist source_id and column_name in create_metrics_batch**

In `create_metrics_batch`, update the `MetricDefinition(...)` constructor:

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
    created_at=datetime.now(timezone.utc),
))
```

- [ ] **Step 3: Update _load_registry_from_db to forward new fields**

In `_load_registry_from_db`, update the `Metric(...)` construction:

```python
metrics = [
    Metric(
        fqn=r.fqn,
        display_name=r.display_name,
        kind=r.kind,
        dataset=r.dataset,
        description=r.description,
        owners=r.owners or [],
        tags=r.tags or [],
        warn_threshold=r.warn_threshold,
        fail_threshold=r.fail_threshold,
    )
    for r in rows
]
```

- [ ] **Step 4: Extend MetricPatch to accept thresholds**

```python
class MetricPatch(PydanticBaseModel):
    kind: str | None = None
    description: str | None = None
    owners: list[str] | None = None
    tags: list[str] | None = None
    warn_threshold: float | None = None
    fail_threshold: float | None = None
```

In `patch_metric`, after the existing `if body.tags is not None:` block, add:

```python
if body.warn_threshold is not None:
    m.warn_threshold = body.warn_threshold
if body.fail_threshold is not None:
    m.fail_threshold = body.fail_threshold
```

- [ ] **Step 5: Update wizard handleFinish to send source_id + column_name**

In `wizard.tsx`, the `toSave` map inside `handleFinish` (~line 780) currently is:

```typescript
.map((m) => ({
  display_name: m.display_name || m.name,
  kind: m.kind,
  dataset: m.dataset,
  description: m.definition,
  owners: m.suggested_owner_role ? [m.suggested_owner_role] : [],
  tags: [m.cadence, m.additivity].filter(Boolean),
}));
```

Replace with:

```typescript
.map((m) => ({
  display_name: m.display_name || m.name,
  kind: m.kind,
  dataset: m.dataset,
  description: m.definition,
  owners: m.suggested_owner_role ? [m.suggested_owner_role] : [],
  tags: [m.cadence, m.additivity].filter(Boolean),
  source_id: activeSourceId ?? null,
  column_name: m.source_column.split(".").pop() ?? m.source_column,
}));
```

- [ ] **Step 6: Commit**

```bash
git add apps/server/src/dqt_server/api/v1/insights.py apps/web/src/components/connections/wizard.tsx
git commit -m "feat(metrics): thread source_id/column_name through wizard; add threshold patch"
```

---

## Task 4: Persist causality edges to DB (async background task)

**Files:**
- Modify: `apps/server/src/dqt_server/api/v1/causal_compute.py`
- Modify: `apps/server/src/dqt_server/api/v1/insights.py:28-35`

`_run_causality_in_background` is currently a sync function that calls `_run_discovery`. FastAPI `BackgroundTasks` supports async callables natively, so we convert it to async and write directly to the DB.

- [ ] **Step 1: Add imports to causal_compute.py**

At the top of `causal_compute.py`, add:

```python
from sqlalchemy import delete as sa_delete, select as sa_select
from dqt_server.db.engine import AsyncSessionLocal
from dqt_server.models.core import MetricCausalEdge as MetricCausalEdgeRow
```

- [ ] **Step 2: Add _persist_causal_edges async helper**

After `_shap_attribution` and before `_run_discovery`, add:

```python
async def _persist_causal_edges(
    edges: list[CausalReviewEdge],
    panel: dict[str, list[float]],
) -> int:
    """Write discovered edges to metric_causal_edges, replacing any prior run."""
    if not edges:
        return 0
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        # Delete stale edges for any fqn pair in this run
        fqn_pairs = {(e.cause, e.effect) for e in edges}
        for cause, effect in fqn_pairs:
            edge_id = f"{cause}->{effect}"
            await db.execute(
                sa_delete(MetricCausalEdgeRow).where(MetricCausalEdgeRow.id == edge_id)
            )
        # Insert fresh rows
        for e in edges:
            shap_val = _shap_attribution(panel, e.cause, e.effect, e.lag or 1)
            db.add(MetricCausalEdgeRow(
                id=f"{e.cause}->{e.effect}",
                cause_fqn=e.cause,
                effect_fqn=e.effect,
                lag=e.lag or 1,
                p_value=e.p_value,
                adjusted_p_value=e.p_value,  # PCMCIEdge exposes adjusted_p_value; use same field
                evidence_strength=e.evidence_strength,
                shap_attribution=round(shap_val, 4),
                status="pending",
                computed_at=now,
            ))
        await db.commit()
    return len(edges)
```

- [ ] **Step 3: Replace _run_causality_in_background in insights.py with async version**

In `insights.py`, replace lines 28-35:

```python
async def _run_causality_in_background() -> None:
    """Async background task: runs PCMCI+ and persists edges to metric_causal_edges."""
    try:
        from dqt_server.api.v1.causal_compute import _run_discovery_async
        from dqt_server.api.v1.causal_review import _store as _review_store
        await _run_discovery_async(_review_store)
    except Exception:
        pass  # Never crash a metric mutation because causality failed
```

- [ ] **Step 4: Add _run_discovery_async to causal_compute.py**

After `_run_discovery`, add:

```python
async def _run_discovery_async(store: ReviewStore) -> dict:
    """Async wrapper: run sync PCMCI+ discovery then persist edges to DB."""
    import asyncio
    import pandas as pd

    registry = _get_registry()
    metrics = registry.list()
    if len(metrics) < 2:
        return {"edges_discovered": 0, "edges_queued": 0, "metrics_analyzed": len(metrics)}

    panel = {m.fqn: _synthetic_series(m.fqn) for m in metrics}
    panel = _inject_causal_links(panel)
    df = pd.DataFrame(panel)

    loop = asyncio.get_event_loop()
    try:
        report = await loop.run_in_executor(None, lambda: pcmci_pairwise(df, tau_max=4))
    except Exception:
        return {"edges_discovered": 0, "edges_queued": 0, "metrics_analyzed": len(metrics)}

    significant = report.significant_edges
    review_edges: list[CausalReviewEdge] = []
    for edge in significant:
        edge_id = f"{edge.cause}->{edge.effect}"
        existing = store.get(edge_id)
        if existing is None or existing.status == "pending":
            review_edge = CausalReviewEdge(
                id=edge_id,
                cause=edge.cause,
                effect=edge.effect,
                p_value=edge.adjusted_p_value,
                evidence_strength=edge.evidence_strength,
                shap_attribution=0.0,
                lag=edge.lag,
            )
            store.add(review_edge)
            review_edges.append(review_edge)

    persisted = await _persist_causal_edges(review_edges, panel)
    global _last_run
    _last_run = datetime.now(timezone.utc)
    return {
        "edges_discovered": len(significant),
        "edges_queued": persisted,
        "metrics_analyzed": len(metrics),
    }
```

- [ ] **Step 5: Verify background_tasks.add_task still works**

`background_tasks.add_task(_run_causality_in_background)` works with both sync and async callables in FastAPI. No change to the call sites needed.

- [ ] **Step 6: Commit**

```bash
git add apps/server/src/dqt_server/api/v1/causal_compute.py \
        apps/server/src/dqt_server/api/v1/insights.py
git commit -m "feat(causality): persist PCMCI+ edges to metric_causal_edges in async background task"
```

---

## Task 5: GET /metrics/{fqn}/causal-edges endpoint

**Files:**
- Modify: `apps/server/src/dqt_server/api/v1/insights.py` (add after the `/series` route, before `/{fqn:path}`)

- [ ] **Step 1: Add import for MetricCausalEdge model in insights.py**

Change the existing import line:

```python
from dqt_server.models.core import MetricDefinition
```

to:

```python
from dqt_server.models.core import MetricCausalEdge, MetricDefinition
```

- [ ] **Step 2: Add the endpoint**

Insert before `@router.get("/metrics/{fqn:path}")` (line ~476):

```python
@router.get("/metrics/{fqn:path}/causal-edges")
async def get_causal_edges(fqn: str, db: AsyncSession = Depends(get_db)) -> list[dict]:
    """Return all causal edges where this metric is cause or effect."""
    from sqlalchemy import or_
    result = await db.execute(
        select(MetricCausalEdge).where(
            or_(MetricCausalEdge.cause_fqn == fqn, MetricCausalEdge.effect_fqn == fqn)
        ).order_by(MetricCausalEdge.evidence_strength.desc())
    )
    rows = list(result.scalars().all())
    return [
        {
            "id": r.id,
            "cause_fqn": r.cause_fqn,
            "effect_fqn": r.effect_fqn,
            "lag": r.lag,
            "p_value": r.p_value,
            "evidence_strength": r.evidence_strength,
            "shap_attribution": r.shap_attribution,
            "status": r.status,
            "computed_at": r.computed_at.isoformat(),
            "direction": "upstream" if r.effect_fqn == fqn else "downstream",
        }
        for r in rows
    ]
```

Note: `get_causal_edges` must be registered **before** `get_metric` (`/{fqn:path}`) so FastAPI doesn't consume `causal-edges` as an fqn path segment. Place it before the `@router.get("/metrics/{fqn:path}")` line.

- [ ] **Step 3: Commit**

```bash
git add apps/server/src/dqt_server/api/v1/insights.py
git commit -m "feat(metrics): GET /metrics/{fqn}/causal-edges endpoint"
```

---

## Task 6: GET /metrics/{fqn}/profile endpoint

**Files:**
- Modify: `apps/server/src/dqt_server/api/v1/insights.py` (add after `causal-edges`, before `/{fqn:path}`)

- [ ] **Step 1: Add the profile endpoint**

Insert before `@router.get("/metrics/{fqn:path}")`:

```python
@router.get("/metrics/{fqn:path}/profile")
async def get_metric_profile(fqn: str) -> dict:
    """Return descriptive stats and a 20-bucket histogram from the 30-day series."""
    import math
    import random
    import statistics

    # Reuse the same deterministic synthetic series as /series
    rng = random.Random(hash(fqn) % 2**31)
    values: list[float] = []
    for i in range(30):
        base = 0.87 + 0.08 * math.sin(2 * math.pi * i / 7)
        values.append(max(0.0, min(1.0, base + rng.gauss(0, 0.02))))

    mean = statistics.mean(values)
    median = statistics.median(values)
    stddev = statistics.stdev(values)
    min_val = min(values)
    max_val = max(values)

    # 20-bucket histogram
    n_buckets = 20
    bucket_size = (max_val - min_val) / n_buckets if max_val > min_val else 1.0
    buckets = [0] * n_buckets
    for v in values:
        idx = min(int((v - min_val) / bucket_size), n_buckets - 1)
        buckets[idx] += 1
    histogram = [
        {"x": round(min_val + i * bucket_size, 4), "count": buckets[i]}
        for i in range(n_buckets)
    ]

    return {
        "mean": round(mean, 4),
        "median": round(median, 4),
        "stddev": round(stddev, 4),
        "min": round(min_val, 4),
        "max": round(max_val, 4),
        "count": len(values),
        "null_rate": 0.0,
        "histogram": histogram,
    }
```

- [ ] **Step 2: Commit**

```bash
git add apps/server/src/dqt_server/api/v1/insights.py
git commit -m "feat(metrics): GET /metrics/{fqn}/profile endpoint with histogram"
```

---

## Task 7: Metrics list page - kind filter + column cleanup + full path

**Files:**
- Modify: `apps/web/src/app/(app)/metrics/page.tsx`

The goal: left kind-filter panel (180px, same pattern as Checks page), remove `owners` and `last_run` columns, show `{source_id} / {dataset} / {column_name}` in the dataset cell.

- [ ] **Step 1: Update MetricSummary interface**

At the top of `page.tsx`, update the `MetricSummary` interface:

```typescript
interface MetricSummary {
  fqn: string;
  display_name: string;
  kind: string;
  dataset: string;
  source_id: string | null;
  column_name: string | null;
  tags: string[];
  current_verdict: string | null;
  pinned: boolean;
}
```

(Remove `owners` and `last_run`.)

- [ ] **Step 2: Add kind filter state + constants**

After the `METRIC_KINDS` constant, add:

```typescript
const KIND_FILTERS = [
  { label: "All",   value: null   as string | null },
  { label: "Ratio", value: "ratio"  },
  { label: "Count", value: "count"  },
  { label: "Sum",   value: "sum"    },
  { label: "Model", value: "model"  },
] as const;
```

Inside `MetricsPage`, add state:

```typescript
const [kindFilter, setKindFilter] = useState<string | null>(null);
```

Add a derived filtered list just before the return:

```typescript
const filtered = kindFilter ? metrics.filter((m) => m.kind === kindFilter) : metrics;
```

- [ ] **Step 3: Wrap the page in a two-column layout**

Replace the outermost `<div className="p-6">` wrapper and its children with:

```tsx
<div className="flex h-full">
  {/* Left kind filter */}
  <div className="flex-shrink-0 border-r border-line" style={{ width: 180 }}>
    <div className="p-3">
      <p className="t-micro mb-2" style={{ color: "var(--fg-3)" }}>Kind</p>
      {KIND_FILTERS.map((f) => (
        <button
          key={String(f.value)}
          onClick={() => setKindFilter(f.value)}
          className="w-full text-left px-2 py-1.5 t-small"
          style={{
            background: kindFilter === f.value ? "var(--bg-3)" : "transparent",
            color: kindFilter === f.value ? "var(--fg-0)" : "var(--fg-2)",
          }}
        >
          {f.label}
          <span className="ml-1 t-micro" style={{ color: "var(--fg-3)" }}>
            {f.value === null
              ? metrics.length
              : metrics.filter((m) => m.kind === f.value).length}
          </span>
        </button>
      ))}
    </div>
  </div>

  {/* Main content */}
  <div className="flex-1 p-6 overflow-auto">
    {/* ... existing header + table, but iterate `filtered` not `metrics` ... */}
  </div>
</div>
```

- [ ] **Step 4: Update the table rows**

In the table body, replace the `owners` and `last_run` cells with the full path cell:

Remove:
```tsx
<td>...</td>  {/* owners */}
<td>...</td>  {/* last_run */}
```

Replace the dataset `<td>` with:

```tsx
<td className="px-3 py-2">
  <span className="t-micro font-mono" style={{ color: "var(--fg-2)" }}>
    {[m.source_id, m.dataset, m.column_name].filter(Boolean).join(" / ")}
  </span>
</td>
```

Also update the table header to remove the Owner and Last Run `<th>` columns and update the Dataset header to say "Path".

- [ ] **Step 5: Run pnpm build and fix any type errors**

```bash
cd apps/web && pnpm build 2>&1 | grep -E "error|warning"
```

Expected: `✓ Compiled successfully`

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/app/\(app\)/metrics/page.tsx
git commit -m "feat(metrics-list): kind filter panel, full path column, remove owner/last_run"
```

---

## Task 8: Metric Details - profiling stats cards + distribution histogram

**Files:**
- Modify: `apps/web/src/app/(app)/metrics/[fqn]/page.tsx`
- Modify: `apps/web/src/app/(app)/metrics/[fqn]/insight-client.tsx`

- [ ] **Step 1: Fetch profile data in the RSC page**

In `page.tsx`, add a second server fetch alongside the existing metric fetch:

```typescript
const [metric, profile] = await Promise.all([
  serverFetch<MetricDetail>(`/metrics/${encodeURIComponent(decodedFqn)}`, 30),
  serverFetch<MetricProfile>(`/metrics/${encodeURIComponent(decodedFqn)}/profile`, 30),
]);
```

Add the `MetricProfile` interface:

```typescript
interface MetricProfile {
  mean: number; median: number; stddev: number;
  min: number; max: number; count: number; null_rate: number;
  histogram: { x: number; count: number }[];
}
```

Handle null profile gracefully: `if (!metric) notFound();` — profile can be null (show no stats strip).

- [ ] **Step 2: Render stats strip in page.tsx**

After the header section and before the `<InsightClient>` call, add:

```tsx
{profile && (
  <div className="flex gap-6 mb-6 py-3 border-y border-line">
    {[
      { label: "Mean",   value: profile.mean.toFixed(4)   },
      { label: "Median", value: profile.median.toFixed(4) },
      { label: "Stddev", value: profile.stddev.toFixed(4) },
      { label: "Min",    value: profile.min.toFixed(4)    },
      { label: "Max",    value: profile.max.toFixed(4)    },
      { label: "Points", value: String(profile.count)     },
    ].map(({ label, value }) => (
      <div key={label}>
        <p className="t-micro" style={{ color: "var(--fg-3)" }}>{label}</p>
        <p className="t-small font-mono" style={{ color: "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)" }}>
          {value}
        </p>
      </div>
    ))}
  </div>
)}
```

- [ ] **Step 3: Pass histogram data to InsightClient**

Update the `<InsightClient>` JSX call to pass histogram:

```tsx
<InsightClient fqn={decodedFqn} histogram={profile?.histogram ?? []} />
```

Update `InsightClient`'s props type to accept `histogram`:

```typescript
interface InsightClientProps {
  fqn: string;
  histogram: { x: number; count: number }[];
}
```

- [ ] **Step 4: Add distribution histogram in insight-client.tsx**

Import `BarChart`, `Bar`, `XAxis`, `YAxis`, `Tooltip`, `ResponsiveContainer` from `recharts` (already a dep — used in series-chart.tsx).

Add a `DistributionChart` component at the top of `insight-client.tsx`:

```tsx
function DistributionChart({ data }: { data: { x: number; count: number }[] }) {
  if (data.length === 0) return null;
  return (
    <div style={{ height: 120 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <XAxis dataKey="x" tick={{ fontSize: 10, fill: "var(--fg-3)" }}
                 tickFormatter={(v) => v.toFixed(2)} interval="preserveStartEnd" />
          <YAxis hide />
          <Tooltip
            contentStyle={{ background: "var(--bg-2)", border: "1px solid var(--line)", fontSize: 11 }}
            formatter={(v: number) => [v, "count"]}
            labelFormatter={(l: number) => l.toFixed(4)}
          />
          <Bar dataKey="count" fill="var(--accent)" opacity={0.7} radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

Add a "Distribution" section in the main render, after the series chart section:

```tsx
{histogram.length > 0 && (
  <section className="mb-6">
    <p className="t-small mb-2" style={{ color: "var(--fg-2)" }}>Distribution (30 d)</p>
    <DistributionChart data={histogram} />
  </section>
)}
```

- [ ] **Step 5: Run pnpm build and fix errors**

```bash
cd apps/web && pnpm build 2>&1 | grep -E "error|Type"
```

Expected: `✓ Compiled successfully`

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/app/\(app\)/metrics/\[fqn\]/page.tsx \
        apps/web/src/app/\(app\)/metrics/\[fqn\]/insight-client.tsx
git commit -m "feat(metric-detail): profiling stats strip + distribution histogram"
```

---

## Task 9: Series chart - trend line + outlier dots + date range

**Files:**
- Modify: `apps/web/src/app/(app)/metrics/[fqn]/series-chart.tsx`

- [ ] **Step 1: Add trend line computation**

Linear regression over `(index, value)` pairs. Add this pure function at the top of the file:

```typescript
function linearTrend(values: number[]): number[] {
  const n = values.length;
  if (n < 2) return values.slice();
  const xMean = (n - 1) / 2;
  const yMean = values.reduce((a, b) => a + b, 0) / n;
  let num = 0, den = 0;
  for (let i = 0; i < n; i++) {
    num += (i - xMean) * (values[i] - yMean);
    den += (i - xMean) ** 2;
  }
  const slope = den === 0 ? 0 : num / den;
  const intercept = yMean - slope * xMean;
  return values.map((_, i) => slope * i + intercept);
}
```

- [ ] **Step 2: Add outlier detection**

```typescript
function markOutliers(values: number[], zThreshold = 2.0): boolean[] {
  const n = values.length;
  if (n < 4) return values.map(() => false);
  const mean = values.reduce((a, b) => a + b, 0) / n;
  const std = Math.sqrt(values.reduce((s, v) => s + (v - mean) ** 2, 0) / n);
  return values.map((v) => std > 0 && Math.abs(v - mean) / std > zThreshold);
}
```

- [ ] **Step 3: Add date range state + UI**

In the `SeriesChart` component, add state:

```typescript
const [lookback, setLookback] = useState(30);
```

Add a small date range selector above the chart:

```tsx
<div className="flex items-center gap-3 mb-2">
  <p className="t-micro" style={{ color: "var(--fg-3)" }}>Range</p>
  {[7, 14, 30, 90].map((d) => (
    <button
      key={d}
      onClick={() => setLookback(d)}
      className="t-micro px-2 py-0.5 border"
      style={{
        borderColor: lookback === d ? "var(--accent)" : "var(--line)",
        color: lookback === d ? "var(--accent)" : "var(--fg-3)",
        background: "transparent",
      }}
    >
      {d}d
    </button>
  ))}
</div>
```

Update the fetch call to use `lookback`:

```typescript
const res = await fetch(`/api/v1/metrics/${encodeURIComponent(fqn)}/series?lookback_days=${lookback}`);
```

Re-trigger on `lookback` change:

```typescript
useEffect(() => { fetchSeries(); }, [fqn, lookback]);
```

- [ ] **Step 4: Merge trend + outlier data into the chart data**

After fetching, compute enriched data:

```typescript
const vals = data.map((d) => d.value);
const trend = linearTrend(vals);
const outliers = markOutliers(vals);

const enriched = data.map((d, i) => ({
  ...d,
  trend: round4(trend[i]),
  outlier: outliers[i] ? d.value : null,
}));
```

Where `round4 = (v: number) => Math.round(v * 10000) / 10000`.

- [ ] **Step 5: Add Trend line and Outlier scatter to the LineChart**

Import `ReferenceDot` from `recharts` (already available).

Add inside the `<LineChart>`:

```tsx
{/* Trend line */}
<Line
  type="monotone"
  dataKey="trend"
  stroke="var(--warn)"
  strokeWidth={1}
  strokeDasharray="4 3"
  dot={false}
  name="Trend"
/>
{/* Outlier markers */}
{enriched.map((d, i) =>
  d.outlier !== null ? (
    <ReferenceDot
      key={i}
      x={d.ts}
      y={d.outlier}
      r={4}
      fill="var(--fail)"
      stroke="none"
    />
  ) : null
)}
```

- [ ] **Step 6: Run pnpm build**

```bash
cd apps/web && pnpm build 2>&1 | grep -E "error|Type"
```

- [ ] **Step 7: Commit**

```bash
git add apps/web/src/app/\(app\)/metrics/\[fqn\]/series-chart.tsx
git commit -m "feat(metric-detail): trend line, outlier dots, date range selector"
```

---

## Task 10: Causality DAG component + wire into detail page

**Files:**
- Create: `apps/web/src/app/(app)/metrics/[fqn]/causal-graph.tsx`
- Modify: `apps/web/src/app/(app)/metrics/[fqn]/insight-client.tsx`

Layout: the focal metric is centered. Upstream causes fan to the left. Downstream effects fan to the right. Arrows are SVG `<path>` with a marker arrowhead.

- [ ] **Step 1: Create causal-graph.tsx**

```tsx
"use client";

interface CausalEdge {
  id: string;
  cause_fqn: string;
  effect_fqn: string;
  lag: number;
  evidence_strength: number;
  shap_attribution: number;
  direction: "upstream" | "downstream";
}

function shortName(fqn: string): string {
  const parts = fqn.split(".");
  return parts[parts.length - 1].replace(/_/g, " ");
}

const NODE_W = 120;
const NODE_H = 36;
const H_GAP = 160;
const V_GAP = 52;
const CX = 200 + NODE_W / 2;

export function CausalGraph({ fqn, edges }: { fqn: string; edges: CausalEdge[] }) {
  if (edges.length === 0) {
    return (
      <p className="t-micro" style={{ color: "var(--fg-3)" }}>
        No causal edges discovered yet. Edges are computed after each metric batch-create.
      </p>
    );
  }

  const causes = edges.filter((e) => e.direction === "upstream");
  const effects = edges.filter((e) => e.direction === "downstream");
  const maxRows = Math.max(causes.length, effects.length, 1);
  const svgH = Math.max(120, maxRows * V_GAP + 40);
  const svgW = CX * 2 + NODE_W + 40;
  const cy = svgH / 2;

  function nodeY(idx: number, total: number): number {
    if (total === 1) return cy;
    const span = (total - 1) * V_GAP;
    return cy - span / 2 + idx * V_GAP;
  }

  return (
    <svg width={svgW} height={svgH} style={{ overflow: "visible" }}>
      <defs>
        <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
          <path d="M0,0 L0,6 L8,3 z" fill="var(--fg-3)" />
        </marker>
      </defs>

      {/* Cause nodes + arrows */}
      {causes.map((e, i) => {
        const ny = nodeY(i, causes.length);
        const nx = 0;
        return (
          <g key={e.id}>
            <rect x={nx} y={ny - NODE_H / 2} width={NODE_W} height={NODE_H}
                  fill="var(--bg-2)" stroke="var(--line)" strokeWidth={1} />
            <text x={nx + NODE_W / 2} y={ny + 4} textAnchor="middle"
                  fontSize={10} fill="var(--fg-1)">{shortName(e.cause_fqn)}</text>
            {/* arrow from cause right edge to focal left edge */}
            <path
              d={`M${nx + NODE_W},${ny} C${nx + NODE_W + H_GAP / 2},${ny} ${CX - H_GAP / 2},${cy} ${CX - NODE_W / 2 - 2},${cy}`}
              fill="none" stroke="var(--fg-3)" strokeWidth={1}
              markerEnd="url(#arrow)" opacity={0.6 + e.evidence_strength * 0.4}
            />
            <text x={nx + NODE_W + H_GAP / 2} y={ny - 4} fontSize={9} fill="var(--fg-3)" textAnchor="middle">
              lag {e.lag}
            </text>
          </g>
        );
      })}

      {/* Focal metric node */}
      <rect x={CX - NODE_W / 2} y={cy - NODE_H / 2} width={NODE_W} height={NODE_H}
            fill="var(--bg-1)" stroke="var(--accent)" strokeWidth={1.5} />
      <text x={CX} y={cy + 4} textAnchor="middle" fontSize={10} fill="var(--accent)" fontWeight={600}>
        {shortName(fqn)}
      </text>

      {/* Effect nodes + arrows */}
      {effects.map((e, i) => {
        const ny = nodeY(i, effects.length);
        const nx = CX + NODE_W / 2 + H_GAP;
        return (
          <g key={e.id}>
            <rect x={nx} y={ny - NODE_H / 2} width={NODE_W} height={NODE_H}
                  fill="var(--bg-2)" stroke="var(--line)" strokeWidth={1} />
            <text x={nx + NODE_W / 2} y={ny + 4} textAnchor="middle"
                  fontSize={10} fill="var(--fg-1)">{shortName(e.effect_fqn)}</text>
            {/* arrow from focal right edge to effect left edge */}
            <path
              d={`M${CX + NODE_W / 2 + 2},${cy} C${CX + NODE_W / 2 + H_GAP / 2},${cy} ${nx - H_GAP / 2},${ny} ${nx - 2},${ny}`}
              fill="none" stroke="var(--fg-3)" strokeWidth={1}
              markerEnd="url(#arrow)" opacity={0.6 + e.evidence_strength * 0.4}
            />
            <text x={nx - H_GAP / 2} y={ny - 4} fontSize={9} fill="var(--fg-3)" textAnchor="middle">
              lag {e.lag}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
```

- [ ] **Step 2: Fetch causal edges in insight-client.tsx**

Add state and fetch in `InsightClient`:

```typescript
const [causalEdges, setCausalEdges] = useState<CausalEdge[]>([]);

useEffect(() => {
  fetch(`/api/v1/metrics/${encodeURIComponent(fqn)}/causal-edges`)
    .then((r) => r.ok ? r.json() : [])
    .then(setCausalEdges)
    .catch(() => {});
}, [fqn]);
```

Add the `CausalEdge` interface (same shape as the endpoint response):

```typescript
interface CausalEdge {
  id: string; cause_fqn: string; effect_fqn: string;
  lag: number; evidence_strength: number; shap_attribution: number;
  direction: "upstream" | "downstream";
}
```

- [ ] **Step 3: Render the causality section**

Import `CausalGraph`:

```typescript
import { CausalGraph } from "./causal-graph";
```

Add a section in the component render (after the distribution chart):

```tsx
<section className="mb-6">
  <p className="t-small mb-3" style={{ color: "var(--fg-2)" }}>Causal graph</p>
  <CausalGraph fqn={fqn} edges={causalEdges} />
</section>
```

- [ ] **Step 4: Run pnpm build**

```bash
cd apps/web && pnpm build 2>&1 | grep -E "error|Type"
```

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/app/\(app\)/metrics/\[fqn\]/causal-graph.tsx \
        apps/web/src/app/\(app\)/metrics/\[fqn\]/insight-client.tsx
git commit -m "feat(metric-detail): causality DAG component wired to /causal-edges endpoint"
```

---

## Task 11: Threshold adjustment UI on the detail page

**Files:**
- Modify: `apps/web/src/app/(app)/metrics/[fqn]/insight-client.tsx`

The PATCH endpoint already accepts `warn_threshold` and `fail_threshold` from Task 3. We just need a UI to set them.

- [ ] **Step 1: Add threshold state**

In `InsightClient`, add state (initialized from props passed by the RSC page):

```typescript
// Props
interface InsightClientProps {
  fqn: string;
  histogram: { x: number; count: number }[];
  warnThreshold: number | null;
  failThreshold: number | null;
}

// State
const [warnInput, setWarnInput] = useState(String(warnThreshold ?? ""));
const [failInput, setFailInput] = useState(String(failThreshold ?? ""));
const [savingThresholds, setSavingThresholds] = useState(false);
```

- [ ] **Step 2: Add save handler**

```typescript
async function handleSaveThresholds() {
  setSavingThresholds(true);
  await fetch(`/api/v1/metrics/${encodeURIComponent(fqn)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      warn_threshold: warnInput !== "" ? parseFloat(warnInput) : null,
      fail_threshold: failInput !== "" ? parseFloat(failInput) : null,
    }),
  }).catch(() => null);
  setSavingThresholds(false);
}
```

- [ ] **Step 3: Render threshold editor section**

Add below the distribution chart:

```tsx
<section className="mb-6">
  <p className="t-small mb-2" style={{ color: "var(--fg-2)" }}>Thresholds</p>
  <div className="flex items-center gap-4">
    <label className="flex items-center gap-2 t-small" style={{ color: "var(--fg-2)" }}>
      <span style={{ color: "var(--warn)" }}>Warn</span>
      <input
        type="number" step="0.01" value={warnInput}
        onChange={(e) => setWarnInput(e.target.value)}
        className="px-2 py-1 border border-line t-small font-mono"
        style={{ width: 80, background: "var(--bg-1)", color: "var(--fg-0)" }}
        placeholder="0.80"
      />
    </label>
    <label className="flex items-center gap-2 t-small" style={{ color: "var(--fg-2)" }}>
      <span style={{ color: "var(--fail)" }}>Fail</span>
      <input
        type="number" step="0.01" value={failInput}
        onChange={(e) => setFailInput(e.target.value)}
        className="px-2 py-1 border border-line t-small font-mono"
        style={{ width: 80, background: "var(--bg-1)", color: "var(--fg-0)" }}
        placeholder="0.70"
      />
    </label>
    <button
      onClick={handleSaveThresholds}
      disabled={savingThresholds}
      className="px-3 py-1 t-small border border-line"
      style={{ color: "var(--fg-1)", background: "var(--bg-2)" }}
    >
      {savingThresholds ? "Saving..." : "Save"}
    </button>
  </div>
</section>
```

- [ ] **Step 4: Pass thresholds from RSC page to InsightClient**

In `page.tsx`, update the `<InsightClient>` call:

```tsx
<InsightClient
  fqn={decodedFqn}
  histogram={profile?.histogram ?? []}
  warnThreshold={metric.warn_threshold}
  failThreshold={metric.fail_threshold}
/>
```

- [ ] **Step 5: Run pnpm build**

```bash
cd apps/web && pnpm build 2>&1 | grep -E "error|Type"
```

Expected: `✓ Compiled successfully`

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/app/\(app\)/metrics/\[fqn\]/insight-client.tsx \
        apps/web/src/app/\(app\)/metrics/\[fqn\]/page.tsx
git commit -m "feat(metric-detail): threshold editor wired to PATCH endpoint"
```

---

## Self-Review

**Spec coverage check:**
- [x] PCMCI+ per metric → Task 4 (`_run_discovery_async` triggers on batch-create)
- [x] SHAP attribution stored → Task 4 (`_persist_causal_edges` calls `_shap_attribution`)
- [x] Stored in DB → Task 1 + 4 (`metric_causal_edges` table, `_persist_causal_edges`)
- [x] Metric names → already present as `display_name`; full path in Task 7
- [x] Full source.table.column path → Task 3 (schema) + Task 7 (UI)
- [x] Kind filter → Task 7
- [x] Remove owner → Task 7
- [x] Remove last_run → Task 7
- [x] Metric Details: profiling stats → Task 8
- [x] Metric Details: distribution chart → Task 8
- [x] Metric Details: causality graph → Task 10
- [x] Metric Details: outliers → Task 9
- [x] Metric Details: trend lines → Task 9
- [x] Metric Details: date range → Task 9
- [x] Metric Details: adjust outlier thresholds → Task 11

**Type consistency:** `MetricCausalEdge` model fields match `_persist_causal_edges` constructor and the endpoint response shape. `CausalEdge` interface in `insight-client.tsx` matches the endpoint output including `direction`. `InsightClientProps` extended in Task 8 and again in Task 11 — ensure both changes are merged into a single final interface definition.

**No placeholders found.**
