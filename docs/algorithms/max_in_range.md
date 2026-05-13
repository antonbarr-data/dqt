# `basic.max_in_range`

> *Max in bounds* — 1.0 if `MAX(col)` falls outside `[min_val, max_val]`; 0.0 otherwise.

## What it checks

Computes `MAX(col)` and tests whether it is within the declared bounds. Returns a binary score: 0.0 (pass) if the maximum is in range, 1.0 (fail) if it is not. No baseline is needed.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `min_val` | `float` | `0.0` | Lower bound (inclusive) |
| `max_val` | `float` | `+inf` | Upper bound (inclusive) |

## Scale (STAT_SCALES)

| Threshold | Value |
|---|---|
| warn | 0.5 |
| fail | 0.5 |
| direction | lower_is_better |

The warn and fail thresholds are both 0.5, so any violation (score = 1.0) is immediately a fail.

## Example

```python
from dqt import Check, Runner, MemoryStore
from dqt.algorithms.basic.numeric_bounds import MaxInRangeDetector

# MaxInRangeDetector(
#     min_val=0.0,            # rarely needed, but useful to assert MAX never goes negative
#     max_val=float("inf"),   # hard physical or business ceiling (e.g. 100.0 for a percentage column)
# )

check = Check(
    schema_name="public",
    table_name="orders",
    column_name="discount_pct",
    detector_slug="max_in_range",
    params={"min_val": 0.0, "max_val": 1.0},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / fail
```

## Compatible with

- Great Expectations: `expect_column_max_to_be_between`
- Soda: `max` (with threshold)

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py`

## When it works well

- Numeric columns where the maximum value should stay within known bounds (e.g. discount rate ≤ 1.0, temperature ≤ 200°C, age ≤ 120).
- Catches single-value spikes that would not move mean/median significantly.

## When it fails / Limitations

- A single legitimate extreme value (a valid large transaction) can fire the check; set bounds with business domain knowledge.
- For skewed distributions, the max is highly variable; consider using `quantile_in_range` at the 99th percentile instead of monitoring the raw maximum.
- FPR at defaults: 0% (rule-based).
- Minimum recommended sample: 1 row.
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based, but wide bounds needed for heavy-tailed data).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Hard upper bound | (default) | (default) | STAT_SCALES defaults |
| Heavy-tailed (revenue, latency) | N/A | N/A | Use quantile_in_range at p99 instead |
| Sparse / high-null | N/A | N/A | Use null_fraction first |

## Failure modes and known limits

`max_in_range` checks the single maximum value in the sample. Because the maximum is the most extreme order statistic, it is highly sensitive to single outliers and to sample size. On heavy-tailed distributions the expected maximum grows with N, so static bounds will produce false positives as data volumes grow.

| Failure mode | Symptom | Fix |
|---|---|---|
| Single legitimate outlier | One real but valid high-value transaction fires the check | Verify the outlier is real; widen the bound or switch to `quantile_in_range` at p99 |
| Sample-size growth raises expected max | As the table grows the maximum creeps up; check fires even though the distribution is stable | Use `quantile_in_range` at p99.9 which is more stable with N growth |
| Data corruption introduces sentinel values | Max jumps to a garbage value (e.g. 9999999 or -1) | Set both a lower and upper bound to catch negative sentinels and overflow values |
| Testing data leaks into production | A test record with an extreme value was not filtered | Add a WHERE clause filter via `sql_assertion_violation` to exclude test rows |
| Stale bounds after business change | Business raised pricing limits but bounds were not updated | Review bounds after any planned pricing or scale changes |

### FPR table

| Data shape | Expected FPR (with correctly set bounds) | Notes |
|---|---|---|
| Normal (mu=100, sigma=20) with bound=200 (5 sigma) | ~0% | Extremely rare to exceed 5 sigma max |
| Lognormal (typical revenue) with wide bound | ~0% | Set bound from historical 99.99th percentile |
| Pareto / power-law (no natural maximum) | Variable | Do not use max_in_range; use quantile_in_range |

### Threshold recommendations

- For hard physical or business ceilings (percentages, ratings, fixed-range IDs): set the bound at the known maximum value. FPR is 0% by definition for clean data.
- For columns without a natural ceiling: do not use `max_in_range`. Use `quantile_in_range` at p99 or p99.9 instead.
- Derive the upper bound from the historical 99.99th percentile of the reference window when no domain ceiling exists.
