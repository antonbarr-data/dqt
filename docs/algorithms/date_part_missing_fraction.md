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

## Source

`packages/dqt/src/dqt/algorithms/basic/date_part.py`
