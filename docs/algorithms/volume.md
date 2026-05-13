# `basic.volume`

> *Row-count change* — fractional deviation of the current row count from the baseline.

## What it checks

Counts rows in the current window, compares to the baseline count fitted from the reference window, and reports `|current / baseline - 1|`. A score of 0.0 means row count is identical to baseline; 0.25 means it has drifted 25% in either direction. Useful for detecting pipeline failures, accidental truncations, or unexpected data surges.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | Baseline row count is fitted automatically from the reference window |

## Scale (STAT_SCALES)

| Threshold | Value |
|---|---|
| warn | 0.10 (10% deviation) |
| fail | 0.25 (25% deviation) |
| direction | lower_is_better |

## Example

```python
from dqt import Check, Runner, MemoryStore
from dqt.algorithms.basic.volume import VolumeDetector

# VolumeDetector()
#   no params — scores total row count against a learned baseline;
#   use row_count_in_range for hard absolute bounds

check = Check(
    schema_name="public",
    table_name="fct_orders",
    detector_slug="volume",
    params={},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / warn / fail
```

## Compatible with

- Great Expectations: `expect_table_row_count_to_be_between`
- Soda: `row_count` (with anomaly detection)
- Elementary: `volume_anomaly`

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/volume.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/volume.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/volume.py`

## When it works well

- Any table where row count is a meaningful data quality signal (expected batch size, daily load volume).
- Simple, stateless check — no reference window needed; set explicit min/max bounds.

## When it fails / Limitations

- Tables with highly variable volumes (event-driven tables, sparse seasonal data) require wide or dynamically adjusted bounds.
- Does not distinguish volume change due to upstream pipeline failures from legitimate business variation; always combine with freshness checks.
- FPR at defaults: 0% (rule-based).
- Minimum recommended sample: 1 row.
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Stable daily load | tight bounds | tight bounds | e.g. ±10% of expected |
| Variable event-driven | wide bounds | wide bounds | e.g. ±50% of expected |
| Seasonal table | N/A | N/A | Use dynamic baseline or row_count_in_range |

## Failure modes and known limits

`volume` computes `|current_count / baseline_count - 1|` as a fractional deviation. Because the score is relative to the fitted baseline, stale baselines are the most common source of false positives. The detector is stateful: if the baseline was fitted on an atypical period the thresholds will be miscalibrated.

| Failure mode | Symptom | Fix |
|---|---|---|
| Baseline fitted on atypical period | A baseline fitted during a campaign or holiday generates a high expected count; normal days fire the lower-bound warn | Re-fit the baseline on a representative 30-day window outside major events |
| Seasonal growth not reflected in baseline | The table grows 5% per month; baseline becomes stale; upper-bound fires monthly | Re-fit quarterly or use a rolling-window baseline |
| Planned maintenance window reduces volume | Expected volume is 0 during a maintenance window; deviation score becomes very large | Snooze the check during maintenance windows; or exclude maintenance windows from the baseline |
| Duplicate load doubles count | A reprocessing job inserts the same data twice; count is 2x baseline | Score correctly fires at 1.0 (100% deviation); investigate the ETL pipeline |
| Single-shard partition failure | One partition of a multi-shard table fails to load; total count drops by 1/N of baseline | The check fires at 1/N deviation; pair with `freshness_seconds_behind` to diagnose partition-level failures |
| Very short baseline window (< 7 days) | Baseline captures too little natural variation; every slight change fires | Always fit on at least 14 days; 30 days is recommended |

### FPR calibration table

| Data shape | Expected FPR at warn=0.10 | Notes |
|---|---|---|
| Stable daily batch (normal variation < 5%) | ~0% | Fractional deviation rarely exceeds 10% for stable pipelines |
| Weekly event-driven (high variation) | ~10-20% | Use wider thresholds (warn=0.25, fail=0.50) or STL anomaly detection |
| Growing table (5% monthly growth) | Increases over time | Re-fit baseline regularly |

### Threshold recommendations

- Default warn=0.10 (10% deviation) / fail=0.25 (25% deviation) is calibrated for stable daily-loaded tables.
- For high-variability event-driven tables: use warn=0.25 / fail=0.50 or switch to `stl_residual_zscore` for trend-aware monitoring.
- Re-fit the baseline at least quarterly; sooner after any planned data model or pipeline change.
