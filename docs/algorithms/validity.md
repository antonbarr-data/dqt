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

det = ValidityDetector(
    sql_predicate="status IN ('pending','active','completed','cancelled')",
    # sql_predicate is a SQL WHERE clause fragment evaluated per row.
    # "price_usd > 0 AND price_usd < 100000" checks both bounds in one check.
    # "email LIKE '%@%'" for quick email sanity.
    # score = fraction of rows where the predicate is FALSE.
)
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

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/validity.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/validity.py)

## Reference

- Redman, T.C. (1996). *Data Quality for the Information Age*. Artech House. (Foundational validity dimension definition.)
- `packages/dqt/src/dqt/algorithms/basic/validity.py`

## Tests

`packages/dqt/tests/algorithms/basic/test_validity.py`

## When it works well

- Columns with a known schema-level type constraint or semantic validation rule (non-negative amounts, valid email, parseable JSON).
- Combines multiple rule checks into a single validity score; useful when you want a holistic "is this column valid?" verdict.

## When it fails / Limitations

- Ambiguous validity definitions require careful specification — too broad misses issues, too strict produces false positives.
- Does not pinpoint which specific rule is violated without inspecting the `evidence` dict.
- FPR at defaults: 0% (rule-based).
- Minimum recommended sample: 1 row.
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Strict validity rule | (default) | (default) | STAT_SCALES defaults |
| Partial validity allowed | 0.01 | 0.05 | Tolerance for edge-case values |
| Sparse / high-null | N/A | N/A | Use null_fraction first |

## Failure modes and known limits

`validity` pushes two SQL aggregations to the warehouse. The predicates are user-supplied SQL and inherit the same failure modes as `sql_assertion_violation`. The score is `validity_rate` (higher is better), unlike most detectors which report a violation fraction.

| Failure mode | Symptom | Fix |
|---|---|---|
| NULL propagation | `status IN ('a','b')` returns NULL (not FALSE) for NULL values; null rows are not counted as invalid by default | Add `status IS NOT NULL AND status IN ('a','b')` if nulls should also fail |
| Predicate too broad | An overly permissive predicate (e.g. `amount >= 0` when amount should be > 0) misses edge cases | Test the predicate against known-invalid rows before deploying |
| Predicate too strict | A strict predicate fires on legitimate edge cases (e.g. `status = 'active'` when 'pending_review' is also valid) | Enumerate all valid values explicitly; audit with the owning team |
| Baseline validity rate not 100% | If the reference window already had invalid rows, the baseline rate is < 1.0; the check's warn/fail band shifts accordingly | Investigate pre-existing invalidity before fitting the baseline; or set a fixed reference rate of 1.0 |
| Warehouse dialect incompatibility | A predicate using REGEXP or JSON functions fails on a different warehouse engine | Use standard SQL in predicates; test on all target engines |
| Score direction confusion | Score is `higher_is_better` (validity rate, not violation fraction); a score of 0.90 is a failure | Ensure alerting and dashboards read direction=higher_is_better correctly |

### FPR calibration table

| Predicate type | Expected FPR | Notes |
|---|---|---|
| Exact set membership (IN list) | 0% | Deterministic; no statistical approximation |
| Range check (amount BETWEEN 1 AND 100) | 0% | Deterministic |
| Statistical predicate (involves STDDEV or PERCENTILE) | Depends on estimator | Rare; use dedicated statistical detectors instead |

### Threshold recommendations

- Default warn=0.95 / fail=0.90 (validity rate) matches STAT_SCALES. This means up to 5% invalid rows triggers a warning.
- For critical columns where any invalidity is a serious issue: lower fail threshold to 0.999 or set `fail_if: "< 1.0"` in YAML.
- For new deployments on columns with known historical invalidity: start with fail=0.80 and tighten after root-cause investigation.
