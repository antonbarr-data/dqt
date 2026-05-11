# `basic.min_in_range`

> *Min in bounds* — 1.0 if `MIN(col)` falls outside `[min_val, max_val]`; 0.0 otherwise.

## What it checks

Computes `MIN(col)` and tests whether it is within the declared bounds. Returns a binary score: 0.0 (pass) if the minimum is in range, 1.0 (fail) if it is not. No baseline is needed.

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
from dqt.algorithms.basic.numeric_bounds import MinInRangeDetector

# MinInRangeDetector(
#     min_val=0.0,            # hard floor (e.g. 0.01 for amounts, 1 for IDs)
#     max_val=float("inf"),   # caps the minimum if it should never be too high
# )

check = Check(
    schema_name="public",
    table_name="orders",
    column_name="amount",
    detector_slug="min_in_range",
    params={"min_val": 0.0, "max_val": 1000000.0},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / fail
```

## Compatible with

- Great Expectations: `expect_column_min_to_be_between`
- Soda: `min` (with threshold)

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py`
