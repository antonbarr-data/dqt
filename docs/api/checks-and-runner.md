# Checks and Runner

## Check model

A `Check` binds a detector to a target column or table, with optional scope, filters, and baseline config.

```python
from dqt import Check, CheckScope, CheckFilter, BaselineConfig

check = Check(
    schema_name="public",           # required
    table_name="gigler_transactions",  # required
    column_name="amount_usd",       # optional — omit for table-level checks
    detector_slug="mad_outlier_fraction",  # required — must be a registered slug
    params={"threshold": 3.5},      # detector-specific parameters
    sample_n=100_000,               # max rows to sample (default: 100_000)
    sampling_pct=25.0,              # sample 25% of rows instead of sample_n
    scope=CheckScope(...),          # optional — restrict which rows to check
    filters=[CheckFilter(...)],     # optional — row-level OR'd filters
    baseline=BaselineConfig(...),   # optional — baseline window config
)
```

### All fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `schema_name` | `str` | required | Database schema |
| `table_name` | `str` | required | Table or view name |
| `column_name` | `str \| None` | `None` | Target column (omit for table-level detectors) |
| `detector_slug` | `str` | required | Registered detector slug |
| `params` | `dict` | `{}` | Detector constructor parameters |
| `sample_n` | `int` | `100_000` | Max rows to sample |
| `sampling_pct` | `float \| None` | `None` | If set, overrides `sample_n` (0–100) |
| `scope` | `CheckScope \| None` | `None` | Row scope restriction |
| `filters` | `list[CheckFilter]` | `[]` | Additional row-level filters |
| `baseline` | `BaselineConfig \| None` | `None` | Baseline window settings |
| `schedule` | `str \| None` | `None` | Cron schedule string (used by server/worker) |
| `id` | `UUID` | auto | Auto-generated check identifier |

---

## CheckScope

Restricts which rows the detector sees.

```python
from dqt import CheckScope

# Entire table (default)
scope = CheckScope(mode="entire")

# Incremental: only rows since a cutoff date
scope = CheckScope(
    mode="incremental",
    key_col="date",
    since="2024-04-01",  # ISO date/datetime, or "last_run"
)

# Custom: arbitrary WHERE clause
scope = CheckScope(
    mode="custom",
    custom_sql="status = 'completed' AND amount_usd > 0",
)
```

**Example — check only Q2 transactions:**

```python
check = Check(
    schema_name="public",
    table_name="gigler_transactions",
    column_name="amount_usd",
    detector_slug="mad_outlier_fraction",
    scope=CheckScope(
        mode="incremental",
        key_col="date",
        since="2024-04-01",
    ),
)
```

---

## CheckFilter

Row-level filters applied before sampling. Multiple filters are AND'd; values within a filter are OR'd.

```python
from dqt import CheckFilter

# Only check Design & Creative transactions
check = Check(
    schema_name="public",
    table_name="gigler_transactions",
    column_name="amount_usd",
    detector_slug="mad_outlier_fraction",
    filters=[
        CheckFilter(col="gig_category", values=["Design & Creative", "AI/ML Development"]),
        CheckFilter(col="status", values=["completed"]),
    ],
)
```

---

## BaselineConfig

Controls the reference window used by statistical detectors during `fit()`.

```python
from dqt import BaselineConfig

baseline = BaselineConfig(
    window_days=14,   # look back this many days for reference data (default: 14)
    min_rows=1_000,   # refuse to fit if fewer rows than this (default: 1_000)
)
```

---

## Runner

Orchestrates fit and score operations against a warehouse adapter.

```python
from dqt import Runner, MemoryStore

store = MemoryStore()
runner = Runner(store)
```

### `runner.fit(check, adapter)`

Establishes the baseline for a check. Reads the reference window from the adapter and caches state in memory.

```python
import pandas as pd
from dqt.adapters.local import LocalAdapter

df_reference = pd.read_csv("examples/gigler/data/gigler_transactions_2024_q1.csv")
adapter = LocalAdapter({"public.gigler_transactions": df_reference})

runner.fit(check, adapter)
```

You only need to call `fit()` explicitly if you want to control the reference data separately. Otherwise `runner.run()` auto-fits on first call.

### `runner.run(check, adapter) → RunResult`

Scores the current data against the fitted baseline. Auto-fits if not already fitted.

```python
df_current = pd.read_csv("examples/gigler/data/gigler_transactions_2024_q2.csv")
adapter_current = LocalAdapter({"public.gigler_transactions": df_current})

result = runner.run(check, adapter_current)
```

### RunResult fields

```python
result.verdict        # Verdict.pass_ | Verdict.warn | Verdict.fail
result.score          # float
result.plain_english  # human-readable verdict string
result.details        # dict — detector-specific breakdown
result.diagnostic_sql # SQL WHERE clause to inspect failing rows (or None)
result.check_id       # UUID
result.detector_slug  # str
result.run_id         # UUID
result.started_at     # datetime
result.finished_at    # datetime
```

---

## MemoryStore

In-memory results store. No persistence across process restarts. Suitable for scripts, notebooks, and CI.

```python
from dqt import MemoryStore

store = MemoryStore()

# After running checks, retrieve results
runs = store.list_runs(check.id, limit=50)
incidents = store.list_incidents(check.id)
incidents_open = store.list_incidents(check.id, status="open")
```

### Incident

Created automatically when a run returns `warn` or `fail`.

```python
incident.severity    # Verdict.warn | Verdict.fail
incident.score       # float
incident.opened_at   # datetime
incident.status      # "open" | "resolved"
incident.check_id    # UUID
incident.run_id      # UUID
```

---

## Running multiple checks

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore
from dqt.adapters.local import LocalAdapter

df = pd.read_csv("examples/gigler/data/gigler_transactions_2024_q2.csv")
adapter = LocalAdapter({"public.gigler_transactions": df})

store = MemoryStore()
runner = Runner(store)

checks = [
    Check(schema_name="public", table_name="gigler_transactions",
          column_name="amount_usd", detector_slug="null_fraction"),
    Check(schema_name="public", table_name="gigler_transactions",
          column_name="amount_usd", detector_slug="mad_outlier_fraction",
          params={"threshold": 3.5}),
    Check(schema_name="public", table_name="gigler_transactions",
          column_name="status", detector_slug="set_membership",
          params={"allowed_values": ["completed", "cancelled", "pending", "refunded"]}),
    Check(schema_name="public", table_name="gigler_transactions",
          column_name="rating", detector_slug="value_in_range",
          params={"min_val": 1.0, "max_val": 5.0}),
    Check(schema_name="public", table_name="gigler_transactions",
          detector_slug="volume"),
]

for check in checks:
    result = runner.run(check, adapter)
    icon = {"pass_": "✓", "warn": "⚠", "fail": "✗"}[result.verdict.value]
    print(f"{icon}  {check.detector_slug:<35} {result.plain_english}")
```
