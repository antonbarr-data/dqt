# Date-part missing fraction (`date_part_missing_fraction`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

Within a rolling lookback window, divides the count of expected time buckets (day/week/month/hour) that contain zero rows by the total expected bucket count. 0.0 means every bucket has at least one row.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `col` | `str` | `"created_at"` | Timestamp column to bucket |
| `granularity` | `str` | `"day"` | `day`, `week`, `month`, or `hour` |
| `lookback_days` | `int` | `30` | Number of days to look back when counting expected buckets |

## Assumptions

- The timestamp column reflects event time in a single, consistent timezone.
- Every bucket in the lookback window is expected to be populated (structural gaps require calibration).
- Granularity is at least coarser than the inter-event arrival interval.

## When it works well

- Daily-loaded fact tables — fires immediately when a day is missing.
- Hourly pipelines where any missing hour is a real outage signal.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Structural gaps (weekends, holidays) | Fires every weekend because pipelines do not run | Use a custom expected-bucket list or restrict `lookback_days` to business days |
| Clock skew places last bucket in the future | Today's bucket appears missing because rows haven't loaded yet | Schedule the check after the daily load; add a 1-bucket grace offset |
| Timezone-naive timestamp column | Rows at midnight UTC land in the wrong local-time bucket | Normalise timestamps to UTC or the desired timezone before bucketing |
| Granularity too fine for data volume | Hourly granularity on a table with 10 rows/day produces mostly empty buckets | Use a granularity coarser than the inter-event interval |

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

No statistical reference; deterministic bucket-count check.

Implementation: `packages/dqt/src/dqt/algorithms/basic/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_orders",
    column_name="created_at",
    detector_slug="date_part_missing_fraction",
    params={'col': 'created_at', 'granularity': 'day', 'lookback_days': 30},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Counts only bucket population, not within-bucket completeness or correctness.
- Requires correct expected-bucket calibration for tables with structural gaps.
