# `basic.row_count_in_range`

> *Row count in range* — 1.0 if the row count in a date window falls outside `[min_rows, max_rows]`; 0.0 otherwise.

## What it checks

Counts rows where `date_col` falls within `[start_date, end_date]` and tests whether the count is within the declared bounds. Returns a binary score: 0.0 (pass) if count is in range, 1.0 (fail) otherwise. No baseline is needed — bounds are declared explicitly. Useful for SLA checks like "fct_orders must have 50–500 rows per day".

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `date_col` | `str` | *(required)* | Date or timestamp column to filter on |
| `start_date` | `str` | *(required)* | Window start (inclusive), ISO format |
| `end_date` | `str` | *(required)* | Window end (inclusive), ISO format |
| `min_rows` | `int` | `0` | Minimum acceptable row count |
| `max_rows` | `int` | `2^31` | Maximum acceptable row count |

## Scale (STAT_SCALES)

| Threshold | Value |
|---|---|
| warn | 0.5 |
| fail | 0.5 |
| direction | lower_is_better |

The warn and fail thresholds are both 0.5, so any violation (score = 1.0) is immediately a fail.

## Example

```python
from dqt import Check, Runner, MemoryStore
from dqt.algorithms.basic.volume import RowCountInRangeDetector

# RowCountInRangeDetector(
#     date_col="created_at",        # partitioning or load timestamp column
#     start_date="2024-01-01",      # SLA window start (inclusive), ISO format
#     end_date="2024-12-31",        # SLA window end (inclusive), ISO format
#     min_rows=0,                   # minimum acceptable load (e.g. 1000 rows/day for a production table)
#     max_rows=2**31,               # ceiling to catch runaway duplicate loads
# )

check = Check(
    schema_name="public",
    table_name="fct_orders",
    detector_slug="row_count_in_range",
    params={
        "date_col": "created_at",
        "start_date": "2024-01-01",
        "end_date": "2024-01-01",
        "min_rows": 50,
        "max_rows": 500,
    },
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / fail
```

## Compatible with

- Great Expectations: `expect_table_row_count_to_be_between`
- Soda: `row_count` (with threshold)

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/volume.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/volume.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/volume.py`

## When it works well

- Batch-loaded tables where the expected row count per run is known and stable.
- Simple, stateless check with explicit min/max bounds that encode the business expectation.

## When it fails / Limitations

- Tables with variable load volumes require frequent threshold updates; consider a drift-based volume check instead for highly variable tables.
- Does not identify *why* the count changed (upstream pipeline failure vs. genuine business change).
- FPR at defaults: 0% (rule-based).
- Minimum recommended sample: 1 row.
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Stable batch load | tight bounds | tight bounds | e.g. expected ± 10% |
| Variable load | wide bounds | wide bounds | e.g. expected ± 50% |
| Seasonal table | N/A | N/A | Use dynamic baseline check |

## Failure modes and known limits

`row_count_in_range` is a deterministic range check on a date-filtered row count. FPR is 0% for clean data with correct bounds. The most common failure mode is stale bounds that no longer reflect actual volume, and date/timezone mismatches in the filter window.

| Failure mode | Symptom | Fix |
|---|---|---|
| Timezone-shifted date filter | `start_date="2024-01-01"` on a UTC column misses rows from non-UTC timezones | Store dates in UTC; or add a CAST AT TIME ZONE clause in the check |
| Daylight saving time boundary | A 23-hour day (DST fall-back) has fewer rows than expected | Add a ±1 hour grace on the date boundaries for hourly checks |
| Incremental load not complete when check runs | The check runs before all rows for the window have been loaded; count appears too low | Schedule the check at least 1 hour after the expected load completion time |
| Holiday or weekend volume drop | Legitimate volume reduction fires the lower bound | Set time-specific bounds (weekday vs weekend) or widen lower bound to account for the minimum expected volume |
| Duplicate load inflates count | A reprocessing job loads the same date window twice; count fires the upper bound | Set max_rows at 2x expected count to catch duplicates; also run `composite_uniqueness` |
| Growing table (absolute bounds go stale) | Row count grows quarter-over-quarter; upper bound fires each quarter | Use percentage-based bounds (e.g. previous_period * 1.2) or switch to the `volume` drift check |

### FPR table

| Scenario | Expected FPR | Notes |
|---|---|---|
| Stable batch load with correct bounds | 0% | Deterministic; only fires when count is genuinely outside range |
| Variable-volume table with wide bounds | 0% if bounds cover historical range | Set bounds from 90th percentile range of historical daily counts |

### Threshold recommendations

- Set min_rows from the historical 5th percentile of daily counts; set max_rows from the 95th percentile.
- For zero-tolerance "must have data" checks: set min_rows=1 and max_rows=unlimited.
- For duplicate-load detection: set max_rows at 1.1x the expected count (tight upper bound).
