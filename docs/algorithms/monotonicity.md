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
