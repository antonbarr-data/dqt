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

## Source

`packages/dqt/src/dqt/algorithms/basic/monotonicity.py`
