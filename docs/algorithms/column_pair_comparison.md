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
from dqt.algorithms.basic.column_pairs import ColumnPairComparisonDetector

det = ColumnPairComparisonDetector(
    col_a="shipped_at",  # left-hand side column name in the DataFrame.
    col_b="created_at",  # right-hand side column name in the DataFrame.
    operator="<=",       # "<=" most common (start ≤ end).
                         # use ">=" for reverse ordering.
                         # use "==" to assert two columns are always equal
                         # (e.g. denormalised copies).
    # score = fraction of rows where the comparison FAILS.
)

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

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/column_pairs.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/column_pairs.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/column_pairs.py`

## When it works well

- Detecting when the statistical relationship (e.g. mean difference, correlation, ratio) between two columns changes over time.
- Useful for cross-column consistency rules (e.g. `gross_amount >= net_amount`, `end_date >= start_date`).

## When it fails / Limitations

- The comparison metric must be appropriate for the column types — comparing a numeric mean to a categorical column produces meaningless results.
- Statistical tests between pairs have reduced power compared to single-column tests at the same sample size.
- FPR at defaults: depends on the comparison metric; rule-based comparisons have 0% FPR.
- Minimum recommended sample: 30 rows for statistical comparisons.
- FPR at defaults on clean normal data: 0% (rule-based) or ~5% (statistical).
- FPR at defaults on heavy-tailed data: ~5–15% for statistical comparisons.

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Deterministic relationship | (default) | (default) | STAT_SCALES defaults |
| Statistical relationship | 0.05 | 0.01 | p-value thresholds |
| Sparse / high-null | N/A | N/A | Use null_fraction first |
