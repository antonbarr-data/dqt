# `basic.freshness_seconds_behind`

> *Data freshness* — seconds elapsed since the most recent row timestamp.

## What it checks

Computes `MAX(col)` and subtracts it from the current UTC wall-clock time. The raw score is the number of seconds since the latest timestamp. Unlike most detectors, freshness uses instance-level thresholds (`warn_seconds`, `fail_seconds`) rather than the global STAT_SCALES thresholds, because freshness SLAs vary per table. If the column contains a naive datetime (no timezone), UTC is assumed.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `col` | `str` | `"updated_at"` | Timestamp column to inspect |
| `warn_seconds` | `float` | `3600` | Seconds behind before warning (default: 1 hour) |
| `fail_seconds` | `float` | `86400` | Seconds behind before failing (default: 24 hours) |

## Scale (STAT_SCALES)

The global scale is shown in the UI gauge but the actual verdict uses the instance thresholds above.

| Threshold | Value |
|---|---|
| warn (global default) | 3600 s (1 h) |
| fail (global default) | 86400 s (24 h) |
| direction | lower_is_better |

## Example

```python
from dqt import Check, Runner, MemoryStore

check = Check(
    schema_name="public",
    table_name="fct_orders",
    detector_slug="freshness_seconds_behind",
    params={"col": "updated_at", "warn_seconds": 3600, "fail_seconds": 86400},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / warn / fail
```

## Compatible with

- Great Expectations: `expect_column_max_to_be_between` (with datetime bounds)
- Soda: `freshness`
- Elementary: `freshness`

## Source

`packages/dqt/src/dqt/algorithms/basic/freshness.py`
