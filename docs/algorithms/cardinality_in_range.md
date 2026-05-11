# `basic.cardinality_in_range`

> *Cardinality in bounds* — 1.0 if `COUNT(DISTINCT col)` falls outside `[min_val, max_val]`; 0.0 otherwise.

## What it checks

Computes `COUNT(DISTINCT col)` and tests whether it is within the declared bounds. Returns a binary score: 0.0 (pass) if cardinality is in range, 1.0 (fail) otherwise. No baseline is needed. Useful for enum-like columns where the number of distinct values should be stable, or to detect runaway dimension tables.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `min_val` | `int` | `1` | Lower bound (inclusive) |
| `max_val` | `int` | `2^31` | Upper bound (inclusive) |

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
    column_name="status",
    detector_slug="cardinality_in_range",
    params={"min_val": 3, "max_val": 6},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / fail
```

## Compatible with

- Great Expectations: `expect_column_unique_value_count_to_be_between`
- Soda: `distinct_count` (with threshold)

## Source

`packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py`
