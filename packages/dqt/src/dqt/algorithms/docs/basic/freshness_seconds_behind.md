# Freshness seconds behind (`freshness_seconds_behind`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

Computes `MAX(col)` and subtracts it from the current UTC wall-clock time. Reports raw seconds since the most recent row. Uses instance-level `warn_seconds` / `fail_seconds` rather than the global STAT_SCALES thresholds because freshness SLAs vary per table.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `col` | `str` | `"updated_at"` | Timestamp column to inspect |
| `warn_seconds` | `float` | `3600` | Seconds behind before warning (default 1 h) |
| `fail_seconds` | `float` | `86400` | Seconds behind before failing (default 24 h) |

## Assumptions

- The timestamp column reliably represents data arrival (`updated_at`, `created_at`, or `loaded_at`).
- Warehouse and service clocks are roughly aligned (the connection-wizard probes clock skew).
- Timestamps are in UTC or have a tzinfo attached; naive timestamps are assumed UTC.

## When it works well

- Streaming or hourly tables where stale data is an immediate signal.
- Daily batches with a defined SLA window (e.g. < 25 h behind).

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Timezone confusion | Warehouse vs local clock mismatch fires false freshness alerts | Always use UTC; verify with `details['warehouse_clock_utc']` |
| Batch ingestion windows | Data refreshed every 6 h fires between batches | Set `warn_seconds` ≥ 1.5 × batch interval |
| No update timestamp column | Some tables have no reliable update column; freshness is undefined | Pair with `row_count_in_range` for ingestion-failure detection |

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

No statistical reference; deterministic SLA check.

Implementation: `packages/dqt/src/dqt/algorithms/basic/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_orders",
    detector_slug="freshness_seconds_behind",
    params={'col': 'updated_at', 'warn_seconds': 3600, 'fail_seconds': 86400},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Cannot tell whether stale data is due to upstream failure or planned maintenance.
- Requires a reliable update timestamp; tables without one cannot be freshness-checked.
