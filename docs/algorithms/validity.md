# `basic.validity`

> *Validity* — measures the fraction of column values that satisfy a SQL predicate; score = validity rate (higher is better), warn below 95 %, fail below 90 %.

## What it does

This is an aggregate detector: instead of sampling rows it pushes two SQL aggregations to the warehouse — `SUM(CASE WHEN NOT (<predicate>) THEN 1 ELSE 0 END)` for the invalid count and `COUNT(*)` for the total. The validity rate is `1 − invalid_count / total`. At fit time it records the baseline validity rate from the reference aggregation result. At score time it computes the current validity rate and returns a `DetectorResult`. Verdict thresholds come from `STAT_SCALES["validity_rate"]` (`warn < 0.95`, `fail < 0.90`). The predicate is injected as a plain SQL boolean expression that the adapter wraps in the aggregate query.

## When to use it

- Enforcing allowed-value constraints on low-cardinality columns: `status IN ('pending','active','completed','cancelled')`, `rating BETWEEN 1 AND 5`, `amount_paid_usd > 0`.
- Any SQL-expressible rule that does not require statistical estimation — use validity for exact rules, use statistical detectors for distributional ones.
- Replacing dbt `accepted_values` tests with continuous monitoring: validity fires on every check run and integrates into the incident lifecycle.
- When the predicate is a business invariant that must hold 100 % of the time but you want graceful degradation alerting (warn at 99 %, fail at 90 %) rather than a hard break.

## When not to use it

- Continuous numeric columns where the "valid range" itself varies over time — use `value_in_range` with a baselined range, or `wasserstein_1` for distributional validity.
- Complex multi-column predicates involving subqueries or CTEs — keep the predicate simple enough to embed in a single `CASE WHEN`; split into multiple checks if needed.
- When the invalid fraction is expected to be non-zero and you want to track its trend over time — pair with `outlier_fraction_drift` on top of this detector's historical rate.
- Cross-table referential constraints — use `referential_integrity_rate` instead.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `sql_predicate` | `str` | `"TRUE"` | A SQL boolean expression evaluated per row. Rows where this is `FALSE` or `NULL` are counted as invalid. The expression must be valid in the target warehouse dialect. |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.95` |
| `fail_threshold` | `0.90` |
| `direction` | `higher_is_better` |
| `score meaning` | Fraction of rows satisfying the predicate; warn when validity rate < 0.95, fail when < 0.90 |

## Example

```python
import pandas as pd
from dqt.algorithms.basic.validity import ValidityDetector

# Simulate the aggregate result rows that the warehouse adapter would return.
# In production the adapter executes the SQL and returns these aggregates.

# Reference period: all bookings have valid status
ref_agg = pd.DataFrame([{"invalid_count": 0, "total_count": 50_000}])

# Current period: 800 rows with an unexpected status value (e.g. "refunded" before enum update)
curr_agg_bad  = pd.DataFrame([{"invalid_count": 800, "total_count": 50_000}])
curr_agg_ok   = pd.DataFrame([{"invalid_count": 12,  "total_count": 50_000}])

det = ValidityDetector(sql_predicate="status IN ('pending','active','completed','cancelled')")
state = det.fit(ref_agg)

result_bad = det.score(curr_agg_bad, state)
print(result_bad.verdict)        # fail  (98.4% valid → below 95%)
print(result_bad.plain_english)  # "98.4% of values are valid (predicate: 'status IN ...')"
print(result_bad.score)          # 0.984 — below warn threshold of 0.95

result_ok = det.score(curr_agg_ok, state)
print(result_ok.verdict)   # pass
print(result_ok.score)     # ~0.9998
```

## Learn more

- 📺 [Data Quality Checks | Data Validation in SQL — Datamites](https://www.youtube.com/watch?v=K1vwArzTsx0) — demonstrates writing SQL-based data quality checks for allowed values, ranges, and referential constraints.

## Reference

- Redman, T.C. (1996). *Data Quality for the Information Age*. Artech House. (Foundational validity dimension definition.)
- `packages/dqt/src/dqt/algorithms/basic/validity.py`

## Tests

`packages/dqt/tests/algorithms/basic/test_validity.py`
