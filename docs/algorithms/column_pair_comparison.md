# `basic.column_pair_comparison`

> *Column pair rule* — fraction of rows where a pairwise column comparison rule is violated.

## What it checks

Evaluates `NOT (col_a <operator> col_b)` for each row where both columns are non-null, and returns the fraction of violations. Supported operators: `>`, `>=`, `<`, `<=`, `=`, `!=`. A score of 0.0 means all non-null row pairs satisfy the rule. Useful for ordering invariants (e.g. `shipped_at >= created_at`) or budget constraints (e.g. `actual_cost <= budget`).

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `col_a` | `str` | `"a"` | Left-hand side column name |
| `col_b` | `str` | `"b"` | Right-hand side column name |
| `operator` | `str` | `">"` | Comparison operator: `>`, `>=`, `<`, `<=`, `=`, `!=` |

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
    detector_slug="column_pair_comparison",
    params={"col_a": "shipped_at", "col_b": "created_at", "operator": ">="},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / warn / fail
```

## Compatible with

- Great Expectations: `expect_column_pair_values_a_to_be_greater_than_b` (and variants)
- Soda: no direct equivalent

## Source

`packages/dqt/src/dqt/algorithms/basic/column_pairs.py`
