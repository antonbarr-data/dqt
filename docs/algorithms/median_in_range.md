# `basic.median_in_range`

> *Median in bounds* — 1.0 if the median falls outside `[min_val, max_val]`; 0.0 otherwise.

## What it checks

Computes `PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY col)` and tests whether it is within the declared bounds. Returns a binary score: 0.0 (pass) if in range, 1.0 (fail) otherwise. No baseline is needed. The median is more robust to outliers than the mean.

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
from dqt.algorithms.basic.numeric_bounds import MedianInRangeDetector

# MedianInRangeDetector(
#     min_val=0.0,            # lower bound of plausible median range
#                             # (e.g. 10 for order amounts — "typical order is at least $10")
#     max_val=float("inf"),   # upper bound of plausible median range
#                             # (e.g. 5000 for order amounts — "typical order is at most $5000")
# )

check = Check(
    schema_name="public",
    table_name="orders",
    column_name="amount",
    detector_slug="median_in_range",
    params={"min_val": 10.0, "max_val": 500.0},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / fail
```

## Compatible with

- Great Expectations: `expect_column_median_to_be_between`
- Soda: `percentile` (with threshold)

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py`

## When it works well

- Numeric columns with known expected median bounds; the median is robust to outliers making this more reliable than `numeric_mean` for skewed columns.
- Preferred over `numeric_mean` for heavy-tailed distributions (revenue, latency, session duration).

## When it fails / Limitations

- For multimodal distributions, the median can fall between modes and may not represent a typical value; use distribution checks instead.
- Requires explicit calibration of min/max median bounds for each column.
- FPR at defaults: 0% (rule-based).
- Minimum recommended sample: 1 row.
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based; median is robust to heavy tails).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Normal bounded | (default) | (default) | STAT_SCALES defaults |
| Heavy-tailed (revenue, latency) | calibrated bounds | calibrated bounds | Median is stable; set tight bounds |
| Sparse / high-null | N/A | N/A | Use null_fraction first |

## Failure modes and known limits

`median_in_range` is a deterministic bound check on the median. It is the most outlier-robust of the central-tendency checks. The main risks are incorrect bound calibration and multimodal distributions where the median falls in a trough between modes.

| Failure mode | Symptom | Fix |
|---|---|---|
| Stale bounds after seasonal shift | Median drifts seasonally (e.g. holiday order values) but bounds were set on non-seasonal data | Set bounds from a full-year historical percentile range; widen by +/- 1 seasonal standard deviation |
| Multimodal distribution (e.g. B2B vs B2C orders) | Median sits in a low-density region between modes; small shifts cause the median to jump between modes | Segment the check by a dimension column (B2B / B2C separately) using a `sql_assertion_violation` |
| Sparse data (< 30 rows) | PERCENTILE_CONT estimate is noisy; median can jump significantly | Increase sample size or widen bounds for small tables |
| Wrong column type (text cast to numeric) | Median of string-encoded numbers is computed after implicit casting; encoding errors produce NULL median | Ensure column is numeric type; use explicit CAST |
| Bounds not updated after pricing change | A planned price change moves the median outside stale bounds | Review and update bounds as part of any planned business change |

### FPR table

| Data shape | Expected FPR (with 30-day calibrated bounds) | Notes |
|---|---|---|
| Normal (symmetric) | ~0% | Median equals mean; bounds from 30-day range cover natural variation |
| Lognormal (revenue, latency) | ~0% | Median is stable even in heavy-tailed distributions |
| Bimodal | Variable | Median falls between modes; bounds calibration is unreliable |

### Threshold recommendations

- Derive bounds from the historical 5th-95th percentile of the column's daily median over at least 30 days.
- For seasonal columns: use the 2nd-98th percentile range over a full year.
- Do not use the raw min/max of the column as bounds - use percentiles of the *median* statistic over time.
