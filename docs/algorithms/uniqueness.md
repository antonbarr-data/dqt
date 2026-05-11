# `basic.uniqueness`

> *Uniqueness* — fraction of distinct values relative to total row count.

## What it checks

Computes `COUNT(DISTINCT col) / COUNT(*)`. A score of 1.0 means every value is unique; lower scores indicate duplicate values. Fits a baseline uniqueness rate on the reference window and includes it in the plain-English output.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | Threshold-based; baseline uniqueness is recorded for display only |

## Scale (STAT_SCALES)

| Threshold | Value |
|---|---|
| warn | 0.95 (below 95% unique) |
| fail | 0.80 (below 80% unique) |
| direction | higher_is_better |

## Example

```python
from dqt import Check, Runner, MemoryStore

check = Check(
    schema_name="public",
    table_name="users",
    column_name="email",
    detector_slug="uniqueness",
    params={},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / warn / fail
```

## Compatible with

- Great Expectations: `expect_column_values_to_be_unique`
- Soda: `duplicate_percent` (inverse)

## Source

`packages/dqt/src/dqt/algorithms/basic/uniqueness.py`
