# `basic.date_part_missing_fraction`

> *Date-part completeness* — fraction of expected date buckets (day/week/month/hour) that contain no rows.

## What it checks

Within a rolling lookback window, counts the number of expected time buckets (e.g. calendar days) that have no rows and divides by the total expected bucket count. A score of 0.0 means every bucket has at least one row; 1.0 means all buckets are empty. Useful for detecting gaps in time-series data (e.g. a missing day of pipeline output).

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `col` | `str` | `"created_at"` | Timestamp column to bucket |
| `granularity` | `str` | `"day"` | Bucket size: `"day"`, `"week"`, `"month"`, or `"hour"` |
| `lookback_days` | `int` | `30` | Number of days to look back when counting expected buckets |

## Scale (STAT_SCALES)

| Threshold | Value |
|---|---|
| warn | 0.01 (1% of buckets missing) |
| fail | 0.05 (5% of buckets missing) |
| direction | lower_is_better |

## Example

```python
from dqt import Check, Runner, MemoryStore
from dqt.algorithms.basic.date_part import DatePartCompletenessDetector

# DatePartCompletenessDetector(
#     col="created_at",      # timestamp/date column to bucket
#     granularity="day",     # "day" for daily (most common); "hour" for hourly pipelines;
#                            # "week"/"month" for slower cadences
#     lookback_days=30,      # 30 covers a full month to catch monthly batch gaps;
#                            # lower to 7 for weekly pipelines
# )

check = Check(
    schema_name="public",
    table_name="fct_orders",
    column_name="created_at",
    detector_slug="date_part_missing_fraction",
    params={"col": "created_at", "granularity": "day", "lookback_days": 30},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / warn / fail
```

## Compatible with

- Great Expectations: `expect_column_values_to_not_be_null` (partial — no bucket awareness)
- Soda: `missing_percent` (partial)

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/date_part.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/date_part.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/date_part.py`

## When it works well

- Date/timestamp columns where certain date parts (weekends, holidays, specific hours) are structurally absent and should be monitored separately from overall completeness.
- Detects ETL pipeline gaps (e.g. "no data loaded for Sundays") that would be masked by an aggregate null_fraction check.

## When it fails / Limitations

- Requires a correct date_part specification (e.g. `dow`, `hour`, `month`) — wrong partitioning produces misleading results.
- Structural absence (e.g. a pipeline that genuinely doesn't produce weekend records) requires threshold calibration to avoid false positives.
- FPR at defaults: 0% (rule-based).
- Minimum recommended sample: 1 row per date part value.
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| All date parts expected | (default) | (default) | STAT_SCALES defaults |
| Known structural gaps | N/A | N/A | Exclude those date parts from check |
| Sparse / high-null | N/A | N/A | Use null_fraction first |
