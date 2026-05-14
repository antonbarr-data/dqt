# Row count in range (`row_count_in_range`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

Counts rows where `date_col` is within `[start_date, end_date]` and returns 1.0 (fail) if outside `[min_rows, max_rows]`, otherwise 0.0. Stateless — bounds are declared.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `date_col` | `str` | `(required)` | Timestamp or date column to filter on |
| `start_date` | `str` | `(required)` | Inclusive window start (ISO format) |
| `end_date` | `str` | `(required)` | Inclusive window end (ISO format) |
| `min_rows` | `int` | `0` | Minimum acceptable row count |
| `max_rows` | `int` | `2**31` | Maximum acceptable row count |

## Assumptions

- `date_col` is in a consistent timezone and the window matches business expectations.
- The check runs after the daily load completes.
- Bounds are derived from historical 5th–95th percentile of daily counts (not arbitrary).

## When it works well

- Daily-loaded batch tables with stable expected volume.
- Duplicate-load detection via tight upper bound.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Timezone-shifted date filter | `start_date='2024-01-01'` on a UTC column misses local-time rows | Store dates in UTC or add `AT TIME ZONE` cast |
| Incremental load not complete | Check runs before all rows loaded; count appears too low | Schedule the check at least 1 h after expected load completion |
| Holiday/weekend volume drop | Legitimate reduction fires the lower bound | Set time-specific bounds or widen the lower bound |
| Duplicate load inflates count | Reprocessing inserts the same window twice | Set `max_rows` at 2× expected to catch duplicates |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | 0% | Deterministic rule; bounds determine FPR exactly |
| Lognormal | 0% | Deterministic rule |
| Poisson | 0% | Deterministic rule |
| Beta | 0% | Deterministic rule |
| Pareto | 0% | Deterministic rule |
| Exponential | 0% | Deterministic rule |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | 0% |
| Lognormal | (default) | 0% |
| Poisson | (default) | 0% |
| Beta | (default) | 0% |
| Pareto | (default) | 0% |
| Exponential | (default) | 0% |

## Citation

No statistical reference; deterministic range check.

Implementation: `packages/dqt/src/dqt/algorithms/basic/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_orders",
    detector_slug="row_count_in_range",
    params={'date_col': 'created_at', 'start_date': '2024-01-01', 'end_date': '2024-01-01', 'min_rows': 50, 'max_rows': 500},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Doesn't identify *why* row count changed (pipeline failure vs business event).
- Static bounds go stale on growing tables; switch to `volume` for fractional drift.
