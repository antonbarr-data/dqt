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

## Failure modes and known limits

`column_pair_comparison` evaluates a row-level comparison rule and returns the violation fraction. The check is deterministic (FPR 0%) for exact rules; the main risk is choosing an operator that does not match the business intent, or having nulls silently excluded when they should be treated as violations.

| Failure mode | Symptom | Fix |
|---|---|---|
| Nulls excluded from denominator | Null rows in either column are skipped; violation rate appears lower than reality | Use `null_fraction` on each column first; treat any null in a mandatory pair as a violation |
| Timezone-offset comparisons | `shipped_at >= created_at` passes when both timestamps are in UTC but fails when one is in local time | Normalise timestamps to UTC at ingest; assert `AT TIME ZONE 'UTC'` in the condition |
| Type mismatch between col_a and col_b | Implicit casting may silently succeed (numeric vs text) or fail with a warehouse error | Ensure both columns are the same type; add explicit CAST in a `sql_assertion_violation` if needed |
| Reversed operator intent | Using `col_a > col_b` when `>=` is correct flags legitimate equal values | Verify operator semantics against the business rule before deploying |
| Clock skew on near-simultaneous events | `shipped_at >= created_at` fires because system clocks differ by milliseconds | Add a grace window via `sql_assertion_violation` with `shipped_at >= created_at - INTERVAL '1 second'` |

### FPR table

All scores are 0% FPR on clean data because this is a deterministic rule evaluation. The only source of false positives is incorrect operator configuration.

| Operator | FPR on clean data | FPR when nulls ignored |
|---|---|---|
| `>=` (ordering) | 0% | 0% (nulls excluded) |
| `=` (equality) | 0% | 0% (nulls excluded) |
| `!=` (inequality) | 0% | 0% (nulls excluded) |

### Threshold recommendations

- Default warn=0.001 / fail=0.01 is appropriate for critical ordering rules.
- For zero-tolerance business invariants (e.g. `shipped_at >= created_at` must always hold), set fail=0 via `fail_if: "> 0"` in YAML.
- For soft cross-column correlations that occasionally break, calibrate thresholds from a 30-day historical violation rate.
