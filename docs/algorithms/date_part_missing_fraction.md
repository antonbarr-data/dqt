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

## Failure modes and known limits

`date_part_missing_fraction` counts expected time buckets vs. populated buckets within the lookback window. It fires when buckets are absent, not when values within a bucket are null or incorrect. The most common failure mode is structural absence being treated as data quality failure.

| Failure mode | Symptom | Fix |
|---|---|---|
| Structural gaps (weekends, holidays) | Check fires every weekend because pipelines don't run on weekends | Use a custom expected-bucket list or set `lookback_days` to span only business days |
| Clock skew places last bucket in future | Rows for "today" haven't loaded yet when the check runs; today's bucket appears missing | Schedule the check after the full daily load; add a 1-bucket grace offset to the lookback |
| Timezone-naive timestamp column | Rows at midnight UTC land in the wrong local-time bucket | Normalise timestamps to UTC or the desired timezone before bucketing |
| Granularity too fine for data volume | Hourly granularity on a table with 10 rows/day produces almost all empty buckets | Choose granularity at least coarser than the expected inter-event interval |
| Lookback too short | A 7-day lookback misses monthly batch gaps | Use `lookback_days` >= the expected batch cadence * 2 |
| All nulls in timestamp column | `null_fraction` on the timestamp column should be checked first; null timestamps produce all-missing buckets | Run `null_fraction` on the timestamp column as a prerequisite check |

### FPR table

| Scenario | Expected FPR | Notes |
|---|---|---|
| Continuous daily-loaded table | 0% | Deterministic; if a bucket is present it passes |
| Table with structural weekend gaps | ~28% per week (2/7 buckets) | Set expected-bucket list excluding weekends |

### Threshold recommendations

- Default warn=0.01 / fail=0.05: appropriate for tables where every calendar day should have data.
- For tables with known structural gaps (weekends, holidays): measure the baseline missing fraction over 90 days and set warn at baseline * 1.5.
- For hourly monitoring of a daily batch: use `granularity="day"` not `"hour"`; hourly gaps are expected within a daily batch.
