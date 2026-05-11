# `basic.sum_in_range`

> *Sum in bounds* — 1.0 if `SUM(col)` falls outside `[min_val, max_val]`; 0.0 otherwise.

## What it checks

Computes `SUM(col)` and tests whether it is within the declared bounds. Returns a binary score: 0.0 (pass) if the sum is in range, 1.0 (fail) otherwise. No baseline is needed. Useful for financial reconciliation checks (e.g. total revenue must be between X and Y).

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

check = Check(
    schema_name="public",
    table_name="daily_revenue",
    column_name="revenue",
    detector_slug="sum_in_range",
    params={"min_val": 10000.0, "max_val": 10000000.0},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / fail
```

## Compatible with

- Great Expectations: `expect_column_sum_to_be_between`
- Soda: `sum` (with threshold)

## Source

`packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py`
