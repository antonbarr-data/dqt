# dqt Web App — Data Profiling Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a data profiling panel to the dqt web app that automatically characterises every column in a dataset — distributions, statistics, quality scores, patterns — so users can explore their data before authoring checks.

**Architecture:** The library's `DistributionProfiler` (Task 7b in Phase 2a) computes column profiles. The server exposes `/api/v1/datasets/{id}/profile` which the web calls. The web renders a multi-column profile grid with histograms, stat gauges, and a quality score card per column. The profile is computed on-demand (or cached for up to 1h) by the arq worker.

**Tech Stack:** FastAPI (server), Next.js 14 App Router + React Server Components (web), Recharts for histograms, shadcn/ui Table + Card, dqt library `DistributionProfiler` + `classify_distribution()`.

**Prerequisites:** Phase 2a library core must be complete (especially Task 7b — DistributionProfiler).

---

## File Map

```
apps/server/src/dqt_server/
├── datasets/
│   ├── routes.py          modify — add GET /datasets/{id}/profile endpoint
│   ├── services/
│   │   └── profiler.py    create — DatasetProfilerService
│   └── schemas/
│       └── profile.py     create — ColumnProfile, DatasetProfile Pydantic models

apps/web/src/
├── app/(app)/datasets/[id]/
│   └── page.tsx           modify — add "Profile" tab
├── modules/datasets/
│   ├── components/
│   │   ├── ProfileGrid.tsx          create — grid of ColumnProfileCard
│   │   ├── ColumnProfileCard.tsx    create — per-column card: type badge, stats, mini histogram, quality score
│   │   ├── ProfileHistogram.tsx     create — Recharts BarChart for value distribution
│   │   └── QualityScoreBar.tsx      create — horizontal bar: completeness, uniqueness, validity
│   ├── hooks/
│   │   └── useDatasetProfile.ts     create — React Query hook for /profile endpoint
│   └── services/
│       └── profileService.ts        create — typed API call
```

---

### Task P1: Server — ColumnProfile schema + profiler service

**Files:**
- Create: `apps/server/src/dqt_server/datasets/schemas/profile.py`
- Create: `apps/server/src/dqt_server/datasets/services/profiler.py`

- [ ] **Step 1: Write failing test**

```python
# apps/server/tests/datasets/test_profiler_service.py
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock


def test_profile_returns_column_profiles():
    from dqt_server.datasets.services.profiler import DatasetProfilerService
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "amount": rng.normal(100, 15, 500),
        "status": ["active" if i % 3 != 0 else None for i in range(500)],
        "id": range(500),
    })
    mock_adapter = MagicMock()
    mock_adapter.sample.return_value = df
    svc = DatasetProfilerService(adapter=mock_adapter)
    profile = svc.profile("public", "orders")
    assert len(profile.columns) == 3
    amount_col = next(c for c in profile.columns if c.name == "amount")
    assert amount_col.completeness_rate > 0.99
    assert amount_col.distribution_type in ("normal", "skewed_positive", "skewed_negative", "heavy_tailed", "uniform", "multimodal", "unknown")


def test_profile_detects_nulls():
    from dqt_server.datasets.services.profiler import DatasetProfilerService
    df = pd.DataFrame({"x": [1.0, None, 3.0, None, 5.0]})
    mock_adapter = MagicMock()
    mock_adapter.sample.return_value = df
    svc = DatasetProfilerService(adapter=mock_adapter)
    profile = svc.profile("public", "t")
    col = profile.columns[0]
    assert pytest.approx(col.null_fraction, abs=0.01) == 0.4
```

- [ ] **Step 2: Create `profile.py` schemas**

```python
# apps/server/src/dqt_server/datasets/schemas/profile.py
from __future__ import annotations
from typing import Any
from pydantic import BaseModel


class ColumnProfile(BaseModel):
    name: str
    data_type: str
    distribution_type: str          # from DistributionType enum
    completeness_rate: float         # 1 - null_fraction
    null_fraction: float
    uniqueness_rate: float           # distinct / total
    row_count: int
    distinct_count: int
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    histogram: list[dict[str, Any]] = []   # [{bucket, count}] for numeric cols
    top_values: list[dict[str, Any]] = []  # [{value, count}] for categorical


class DatasetProfile(BaseModel):
    schema_name: str
    table_name: str
    row_count: int
    column_count: int
    columns: list[ColumnProfile]
    profiled_at: str    # ISO datetime
```

- [ ] **Step 3: Create `profiler.py` service**

```python
# apps/server/src/dqt_server/datasets/services/profiler.py
from __future__ import annotations
from datetime import datetime, timezone
import numpy as np
import pandas as pd

from dqt.adapters._protocol import WarehouseAdapter
from dqt.algorithms.distribution.profiler import classify_distribution, DistributionType
from dqt_server.datasets.schemas.profile import ColumnProfile, DatasetProfile


class DatasetProfilerService:
    def __init__(self, adapter: WarehouseAdapter) -> None:
        self._adapter = adapter

    def profile(self, schema: str, table: str, sample_n: int = 100_000) -> DatasetProfile:
        df = self._adapter.sample(schema, table, n=sample_n)
        row_count = len(df)
        columns = [self._profile_column(df[col]) for col in df.columns]
        return DatasetProfile(
            schema_name=schema,
            table_name=table,
            row_count=row_count,
            column_count=len(df.columns),
            columns=columns,
            profiled_at=datetime.now(timezone.utc).isoformat(),
        )

    def _profile_column(self, series: pd.Series) -> ColumnProfile:
        name = series.name
        data_type = str(series.dtype)
        total = len(series)
        null_count = int(series.isna().sum())
        null_fraction = null_count / total if total > 0 else 0.0
        completeness_rate = 1.0 - null_fraction
        non_null = series.dropna()
        distinct_count = int(non_null.nunique())
        uniqueness_rate = distinct_count / total if total > 0 else 0.0

        is_numeric = pd.api.types.is_numeric_dtype(series)
        min_val = max_val = mean_val = median_val = std_val = None
        histogram: list[dict] = []
        top_values: list[dict] = []
        dist_type = "unknown"

        if is_numeric and len(non_null) >= 8:
            arr = non_null.to_numpy(dtype=float)
            min_val = float(arr.min())
            max_val = float(arr.max())
            mean_val = float(arr.mean())
            median_val = float(np.median(arr))
            std_val = float(arr.std())
            profile = classify_distribution(arr)
            dist_type = profile.distribution_type.value
            counts, edges = np.histogram(arr, bins=min(20, distinct_count))
            histogram = [
                {"bucket": float(edges[i]), "count": int(counts[i])}
                for i in range(len(counts))
            ]
        else:
            value_counts = non_null.value_counts().head(10)
            top_values = [{"value": str(k), "count": int(v)} for k, v in value_counts.items()]

        return ColumnProfile(
            name=name, data_type=data_type, distribution_type=dist_type,
            completeness_rate=completeness_rate, null_fraction=null_fraction,
            uniqueness_rate=uniqueness_rate, row_count=total, distinct_count=distinct_count,
            min=min_val, max=max_val, mean=mean_val, median=median_val, std=std_val,
            histogram=histogram, top_values=top_values,
        )
```

- [ ] **Step 4: Run tests, commit**
```bash
cd apps/server && uv run pytest tests/datasets/test_profiler_service.py -v
git add apps/server/src/dqt_server/datasets/schemas/profile.py \
        apps/server/src/dqt_server/datasets/services/profiler.py \
        apps/server/tests/datasets/test_profiler_service.py
git commit -m "feat(server): DatasetProfilerService — column-level distribution + quality profiling"
```

---

### Task P2: Server — `/api/v1/datasets/{id}/profile` endpoint

**Files:**
- Modify: `apps/server/src/dqt_server/datasets/routes.py` — add `GET /datasets/{id}/profile`

- [ ] **Step 1: Write failing test**

```python
# apps/server/tests/datasets/test_profile_route.py
from unittest.mock import patch, MagicMock
import pytest


def test_get_dataset_profile(client, fixture_admin_user):
    """GET /api/v1/datasets/{id}/profile returns a DatasetProfile."""
    with patch("dqt_server.datasets.routes.DatasetProfilerService") as MockSvc:
        mock_profile = MagicMock()
        mock_profile.model_dump.return_value = {
            "schema_name": "public", "table_name": "orders",
            "row_count": 500, "column_count": 3, "columns": [], "profiled_at": "2026-01-01T00:00:00Z"
        }
        MockSvc.return_value.profile.return_value = mock_profile
        response = client.get("/api/v1/datasets/test-dataset-id/profile")
    assert response.status_code == 200
    data = response.json()
    assert "columns" in data
```

- [ ] **Step 2: Add route**

```python
# In apps/server/src/dqt_server/datasets/routes.py — add this endpoint:

@router.get("/{dataset_id}/profile", response_model=DatasetProfile)
async def get_dataset_profile(
    dataset_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DatasetProfile:
    dataset = await DatasetRepository(db, current_user.tenant_id).get(dataset_id)
    adapter = await build_adapter_for_dataset(dataset, db, current_user.tenant_id)
    svc = DatasetProfilerService(adapter=adapter)
    return svc.profile(dataset.schema_name, dataset.table_name)
```

- [ ] **Step 3: Run tests, commit**
```bash
git commit -m "feat(server): GET /datasets/{id}/profile endpoint"
```

---

### Task P3: Web — ProfileGrid + ColumnProfileCard components

**Files:**
- Create: `apps/web/src/modules/datasets/components/ProfileHistogram.tsx`
- Create: `apps/web/src/modules/datasets/components/ColumnProfileCard.tsx`
- Create: `apps/web/src/modules/datasets/components/ProfileGrid.tsx`
- Create: `apps/web/src/modules/datasets/hooks/useDatasetProfile.ts`
- Modify: `apps/web/src/app/(app)/datasets/[id]/page.tsx` — add "Profile" tab

**`ProfileHistogram.tsx`** — Recharts BarChart rendering `histogram[]` from `ColumnProfile`. Width 100%, height 80px, no axes, fill `var(--accent)`.

**`ColumnProfileCard.tsx`** — Card showing:
- Header: column name + data type badge + distribution type badge
- Stats row: completeness %, null %, unique %, row count
- Histogram (numeric) or top-values bar chart (categorical)
- `<StatGauge metric="completeness_rate" value={completenessRate} />`

**`ProfileGrid.tsx`** — CSS grid (`repeat(auto-fill, minmax(320px, 1fr))`), renders one `ColumnProfileCard` per column.

**`useDatasetProfile.ts`** — React Query hook: `useQuery({ queryKey: ['profile', datasetId], queryFn: () => profileService.getProfile(datasetId) })`

- [ ] **Step 1: Implement components (TDD with Vitest)**

```typescript
// apps/web/src/modules/datasets/__tests__/ColumnProfileCard.test.tsx
import { render, screen } from '@testing-library/react'
import { ColumnProfileCard } from '../components/ColumnProfileCard'

const mockColumn = {
  name: 'amount', data_type: 'float64', distribution_type: 'normal',
  completeness_rate: 0.99, null_fraction: 0.01, uniqueness_rate: 0.95,
  row_count: 1000, distinct_count: 950,
  min: 50, max: 200, mean: 100, median: 99, std: 15,
  histogram: [{ bucket: 50, count: 10 }, { bucket: 70, count: 50 }],
  top_values: [],
}

test('renders column name', () => {
  render(<ColumnProfileCard column={mockColumn} />)
  expect(screen.getByText('amount')).toBeInTheDocument()
})

test('renders completeness rate', () => {
  render(<ColumnProfileCard column={mockColumn} />)
  expect(screen.getByText(/99/)).toBeInTheDocument()
})
```

- [ ] **Step 2: Add Profile tab to dataset page**

In `apps/web/src/app/(app)/datasets/[id]/page.tsx`, add a `"Profile"` tab alongside Overview / Tests / Lineage / Samples. The tab content renders `<ProfileGrid datasetId={id} />`.

- [ ] **Step 3: `pnpm build` — fix all errors**

- [ ] **Step 4: Commit**
```bash
git commit -m "feat(web): data profiling panel — ProfileGrid, ColumnProfileCard, histogram, quality gauges"
```

---

## Dataplex rule coverage in profiling UI

The profiling panel surfaces the following Dataplex rule categories automatically without requiring the user to author checks:
- **Completeness** — `null_fraction` and `completeness_rate` per column
- **Uniqueness** — `uniqueness_rate` per column
- **Distribution type** — automatic via `classify_distribution()` — guides check authoring
- **Range** — `min` / `max` / `mean` / `std` shown per column — user can click to create a range check
- **Pattern** — top_values list flags unexpected categorical values
- **Freshness** — shown as a column-level stat when the column is a timestamp

The "Create check from profile" shortcut (click any stat → auto-fills check authoring) is a Phase 5 UX feature.
