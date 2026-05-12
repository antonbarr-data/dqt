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
from dqt.algorithms.basic.freshness import FreshnessDetector

det = FreshnessDetector(
    col="updated_at",       # the timestamp column to check.
    warn_seconds=3600,      # 3600 (1 hour) for hourly pipelines.
                            # for daily pipelines use warn_seconds=86400.
                            # for near-real-time use warn_seconds=300 (5 min).
    fail_seconds=86400,     # 86400 (24 hours) for daily pipelines.
                            # for daily pipelines use fail_seconds=172800 (2 days).
                            # for near-real-time use fail_seconds=900 (15 min).
)

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

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/freshness.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/freshness.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/freshness.py`

## When it works well

- Any table where data should arrive within a known SLA (e.g. event streams should be < 300s behind, daily tables < 86400s behind).
- Stateless — no reference window needed; compare `max(updated_at)` to `now()`.

## When it fails / Limitations

- Tables without a reliable `updated_at` or `created_at` timestamp column cannot be freshness-checked; use `volume` or `row_count_in_range` instead.
- Scheduled batch tables will always appear stale between runs — set the `warn` threshold larger than the batch interval.
- Clock skew between the warehouse and the dqt service can produce false positives; the health-check protocol includes a clock-skew probe to detect this.
- FPR at defaults: 0% (rule-based).
- Minimum recommended sample: 1 row.
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Streaming table | 300 | 900 | Seconds; SLA-driven |
| Daily batch table | 90000 | 172800 | ~25h warn, 48h fail |
| Irregular / on-demand | N/A | N/A | Use manual SLA or skip this check |

## Failure modes and known limits

| Failure mode | Symptom | Fix |
|---|---|---|
| Timezone confusion | Warehouse clock vs local clock mismatch causes false freshness violations | Always use UTC timestamps; check `details["warehouse_clock_utc"]` |
| Batch ingestion windows | Data is refreshed every 6h; freshness fires between batches | Set `max_seconds_behind` to batch interval * 1.5 for tolerance |
| No max_updated_at column | Some tables have no update timestamp; freshness is approximate | Pair with a row-count check to detect ingestion failure |
