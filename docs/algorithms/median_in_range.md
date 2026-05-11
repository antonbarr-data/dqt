# `basic.median_in_range`

> *Median in bounds* — 1.0 if the median falls outside `[min_val, max_val]`; 0.0 otherwise.

## What it checks

Computes `PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY col)` and tests whether it is within the declared bounds. Returns a binary score: 0.0 (pass) if in range, 1.0 (fail) otherwise. No baseline is needed. The median is more robust to outliers than the mean.

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
    table_name="orders",
    column_name="amount",
    detector_slug="median_in_range",
    params={"min_val": 10.0, "max_val": 500.0},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / fail
```

## Compatible with

- Great Expectations: `expect_column_median_to_be_between`
- Soda: `percentile` (with threshold)

## Source

`packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py`
