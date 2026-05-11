# `basic.sql_assertion_violation`

> *SQL assertion violation* — fraction of rows failing a custom SQL condition.

## What it checks

Evaluates `NOT (condition)` for each row and returns the fraction of violations. The `condition` is a trusted SQL boolean expression provided at check-definition time (not at runtime). A score of 0.0 means all rows satisfy the condition. This is the escape hatch for any rule not covered by the other declarative checks. The condition is embedded directly into the aggregation SQL so it has access to all columns in the table.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `condition` | `str` | *(required)* | SQL boolean expression that should be true for every valid row (e.g. `amount > 0 AND status IS NOT NULL`) |

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
    detector_slug="sql_assertion_violation",
    params={"condition": "amount > 0 AND status IS NOT NULL AND customer_id IS NOT NULL"},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / warn / fail
```

## Compatible with

- Great Expectations: `expect_column_pair_values_to_be_equal` (partial); use `SqlAlchemyDataset` for custom SQL
- Soda: `failed_rows` (with custom SQL)
- Dataplex: `SqlAssertion` rule

## Source

`packages/dqt/src/dqt/algorithms/basic/sql_assertion.py`
