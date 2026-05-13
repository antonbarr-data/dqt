# `basic.monotonicity`

> *Monotonicity* — 1.0 if the sequence violates monotonic ordering; 0.0 if it is monotonic.

## What it checks

Takes the first numeric column of the sampled DataFrame (after dropping nulls), computes consecutive differences with `numpy.diff`, and checks whether all differences are `>= 0` (increasing) or `<= 0` (decreasing). Returns 0.0 if the sequence is monotonic, 1.0 otherwise. Useful for sequence IDs, auto-increment columns, or cumulative metrics that must never decrease.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `direction` | `str` | `"increasing"` | Expected ordering: `"increasing"` (non-decreasing) or `"decreasing"` (non-increasing) |

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
from dqt.algorithms.basic.monotonicity import MonotonicityDetector

det = MonotonicityDetector(
    direction="increasing",
    # "increasing" for counters, IDs, cumulative sums.
    # "decreasing" for countdown timers or deprecating inventories.
    # score = fraction of consecutive pairs that violate the direction.
)

check = Check(
    schema_name="public",
    table_name="events",
    column_name="event_sequence_id",
    detector_slug="monotonicity",
    params={"direction": "increasing"},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / fail
```

## Compatible with

- Great Expectations: `expect_column_values_to_be_increasing` / `expect_column_values_to_be_decreasing`
- Soda: no direct equivalent

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/monotonicity.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/monotonicity.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/monotonicity.py`

## When it works well

- Sequence or ID columns that should strictly increase (auto-increment IDs, version numbers, monotonically increasing timestamps).
- Event sequence tables where out-of-order records indicate a data quality issue.

## When it fails / Limitations

- Reprocessing or late-arriving data may produce non-monotonic sequences that are legitimate — set the check to `warn` rather than `fail` for such tables.
- Requires ordering by a specific column — ordering is applied in the check definition.
- FPR at defaults: 0% (rule-based).
- Minimum recommended sample: 2 rows.
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Strict monotonic column | (default) | (default) | STAT_SCALES defaults |
| Near-monotonic (late arrivals) | 0.001 | 0.01 | Small tolerance for out-of-order |
| Non-monotonic by design | N/A | N/A | Not applicable |

## Failure modes and known limits

`monotonicity` checks whether the sampled column values are non-decreasing (or non-increasing) after sorting by the row order returned by the query. The check result depends critically on the ORDER BY clause in the sample query. If the query does not order by the intended sequence column, the check produces meaningless results.

| Failure mode | Symptom | Fix |
|---|---|---|
| Sample not ordered by sequence column | The check evaluates random row order; passes or fails non-deterministically | Always specify `ORDER BY sequence_col` in the check's sample query or adapter params |
| Backfills / late-arriving records | A historical record is inserted after newer records; the sequence has a dip | Use `warn` instead of `fail` for tables with known late arrivals; or filter by inserted_at |
| Time-zone offset on timestamp column | UTC timestamps ordered correctly but local-time rendering looks non-monotonic in the UI | Store and compare in UTC; do not convert timezone in the sequence column |
| Auto-increment gaps after deletes | Sequence ID has gaps (e.g. 1, 2, 5, 6) but is still monotonic; check passes correctly | Gaps are fine - only direction matters; use `uniqueness` to detect missing IDs |
| Cumulative metric that resets | A running total resets to zero at the start of each period | Scope the check to a single period window; or exclude reset points with a SQL filter |
| Composite sort key needed | The natural order requires sorting by (date, id) not just id | Use a `sql_assertion_violation` with `LAG()` window function for multi-key ordering checks |

### FPR table

| Scenario | Expected FPR | Notes |
|---|---|---|
| True monotonic sequence (correct ORDER BY) | 0% | Fully deterministic |
| Out-of-order sample (missing ORDER BY) | Unpredictable | Always specify sort order |
| Late-arrival rate 0.5% | ~0.5% "false positive" rate | These are real violations; configure warn threshold accordingly |

### Threshold recommendations

- For strict sequence columns (auto-increment IDs, event IDs): set fail=0 (any violation is a real incident).
- For tables with expected late arrivals: measure the historical late-arrival rate and set warn at 2x that rate.
- For cumulative metrics with known resets: do not use `monotonicity`; use `value_in_range` per period instead.
