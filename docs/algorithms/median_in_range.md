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
