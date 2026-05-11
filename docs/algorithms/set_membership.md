# `basic.set_membership`

> *Set membership* — fraction of values not in the allowed set.

## What it checks

Evaluates `col NOT IN (allowed_values)` for each row and returns the fraction of violations. A score of 0.0 means all values are members of the allowed set. Null values count as violations (not in the set). The allowed set is quoted as string literals in the SQL; cast to the column type as needed.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `allowed_values` | `list` or `set` | *(required, non-empty)* | The complete set of permitted values |

## Scale (STAT_SCALES)

| Threshold | Value |
|---|---|
| warn | 0.001 (0.1% violations) |
| fail | 0.01 (1% violations) |
| direction | lower_is_better |

## Example

```python
from dqt import Check, Runner, MemoryStore

check = Check(
    schema_name="public",
    table_name="orders",
    column_name="status",
    detector_slug="set_membership",
    params={"allowed_values": ["pending", "paid", "shipped", "cancelled"]},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / warn / fail
```

## Compatible with

- Great Expectations: `expect_column_values_to_be_in_set`
- Soda: `valid_values`

## Source

`packages/dqt/src/dqt/algorithms/basic/value_checks.py`
