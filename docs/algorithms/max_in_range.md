# `basic.max_in_range`

> *Max in bounds* — 1.0 if `MAX(col)` falls outside `[min_val, max_val]`; 0.0 otherwise.

## What it checks

Computes `MAX(col)` and tests whether it is within the declared bounds. Returns a binary score: 0.0 (pass) if the maximum is in range, 1.0 (fail) if it is not. No baseline is needed.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `min_val` | `float` | `0.0` | Lower bound (inclusive) |
| `max_val` | `float` | `+inf` | Upper bound (inclusive) |

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
from dqt.algorithms.basic.numeric_bounds import MaxInRangeDetector

# MaxInRangeDetector(
#     min_val=0.0,            # rarely needed, but useful to assert MAX never goes negative
#     max_val=float("inf"),   # hard physical or business ceiling (e.g. 100.0 for a percentage column)
# )

check = Check(
    schema_name="public",
    table_name="orders",
    column_name="discount_pct",
    detector_slug="max_in_range",
    params={"min_val": 0.0, "max_val": 1.0},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / fail
```

## Compatible with

- Great Expectations: `expect_column_max_to_be_between`
- Soda: `max` (with threshold)

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py`
