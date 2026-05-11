# `basic.completeness`

> *Completeness* — fraction of non-null values; complement of `null_fraction`.

## What it checks

Computes `1 - (null_count / total_count)`. A score of 1.0 means all values are present; 0.0 means the column is entirely null. Fits a baseline completeness rate on the reference window and reports both current and baseline in the plain-English output.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | Threshold-based; baseline completeness is recorded for display only |

## Scale (STAT_SCALES)

| Threshold | Value |
|---|---|
| warn | 0.95 (below 95% complete) |
| fail | 0.90 (below 90% complete) |
| direction | higher_is_better |

## Example

```python
from dqt import Check, Runner, MemoryStore

check = Check(
    schema_name="public",
    table_name="orders",
    column_name="email",
    detector_slug="completeness",
    params={},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / warn / fail
```

## Compatible with

- Great Expectations: `expect_column_values_to_not_be_null`
- Soda: `missing_percent` (inverse)

## Source

`packages/dqt/src/dqt/algorithms/basic/completeness.py`
