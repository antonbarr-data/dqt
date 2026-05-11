# `basic.value_in_range`

> *Values in range* — fraction of rows where the column value falls outside `[min_val, max_val]`.

## What it checks

Evaluates `col < min_val OR col > max_val` for each row and returns the fraction of violations. A score of 0.0 means all values are within bounds. No baseline is needed — bounds are declared explicitly. The failing filter SQL is set so the UI can drill into violating rows.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `min_val` | `float` | `-inf` | Lower bound (inclusive) |
| `max_val` | `float` | `+inf` | Upper bound (inclusive) |

## Scale (STAT_SCALES)

| Threshold | Value |
|---|---|
| warn | 0.001 (0.1% out of range) |
| fail | 0.01 (1% out of range) |
| direction | lower_is_better |

## Example

```python
from dqt import Check, Runner, MemoryStore
from dqt.algorithms.basic.value_checks import ValueInRangeDetector

# ValueInRangeDetector(
#     min_val=float("-inf"),  # lower bound — set to domain floor (e.g. 0.01 for price_usd,
#                             # 1.0 for rating, 0.0 for percentages); default means unchecked
#     max_val=float("inf"),   # upper bound — set to domain ceiling (e.g. 50000 for price_usd,
#                             # 5.0 for rating, 1.0 for percentages); default means unchecked
# )

check = Check(
    schema_name="public",
    table_name="orders",
    column_name="amount",
    detector_slug="value_in_range",
    params={"min_val": 0.0, "max_val": 100000.0},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / warn / fail
```

## Compatible with

- Great Expectations: `expect_column_values_to_be_between`
- Soda: `valid_min` / `valid_max`

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/value_checks.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/value_checks.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/value_checks.py`
