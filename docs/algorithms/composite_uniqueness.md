# `basic.composite_uniqueness`

> *Composite key uniqueness* — fraction of rows that are duplicates on a multi-column key.

## What it checks

Concatenates the specified key columns into a single composite key string (null-safe), counts total rows versus distinct composite values, and returns the duplicate fraction `(total - distinct) / total`. A score of 0.0 means all composite key values are unique; 1.0 means every row is a duplicate.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `key_columns` | `list[str]` | *(required)* | List of column names that together form the composite key |

## Scale (STAT_SCALES)

| Threshold | Value |
|---|---|
| warn | 0.001 (0.1% duplicate rows) |
| fail | 0.01 (1% duplicate rows) |
| direction | lower_is_better |

## Example

```python
from dqt import Check, Runner, MemoryStore

check = Check(
    schema_name="public",
    table_name="order_items",
    detector_slug="composite_uniqueness",
    params={"key_columns": ["order_id", "product_id"]},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / warn / fail
```

## Compatible with

- Great Expectations: `expect_compound_columns_to_be_unique`
- Soda: `duplicate_count` (on multi-column group)

## Source

`packages/dqt/src/dqt/algorithms/basic/column_pairs.py`
