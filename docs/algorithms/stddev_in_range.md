# `basic.stddev_in_range`

> *Stddev in bounds* — 1.0 if `STDDEV(col)` falls outside `[min_val, max_val]`; 0.0 otherwise.

## What it checks

Computes `STDDEV(col)` and tests whether it is within the declared bounds. Returns a binary score: 0.0 (pass) if in range, 1.0 (fail) otherwise. No baseline is needed. Useful for detecting unexpected variance collapse (e.g. a constant feed) or variance explosion (e.g. data corruption).

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
from dqt.algorithms.basic.numeric_bounds import StddevInRangeDetector

# StddevInRangeDetector(
#     min_val=0.0,            # set > 0 to detect suspiciously constant data
#                             # (stddev = 0 = all-same values = likely pipeline bug)
#     max_val=float("inf"),   # catch runaway variance (e.g. 1000 on a column normally spread 0–200
#                             # would catch a suddenly wild distribution)
# )

check = Check(
    schema_name="public",
    table_name="sensor_readings",
    column_name="temperature",
    detector_slug="stddev_in_range",
    params={"min_val": 0.1, "max_val": 50.0},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / fail
```

## Compatible with

- Great Expectations: `expect_column_stdev_to_be_between`
- Soda: `stddev` (with threshold)

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py`

## When it works well

- Monitoring variance stability in numeric columns where the spread should remain within known bounds.
- Useful for detecting variance explosions (data engineering errors that introduce extreme values) or variance collapses (degenerate data).

## When it fails / Limitations

- Standard deviation is sensitive to outliers — a single extreme value can inflate the std significantly.
- Heavy-tailed distributions have inherently high variance; use robust scale measures (MAD or IQR-based) for monitoring spread in skewed columns.
- FPR at defaults: 0% (rule-based).
- Minimum recommended sample: 2 rows.
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based, but bounds must be calibrated for heavy tails).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Normal bounded variance | calibrated bounds | calibrated bounds | Derive from reference window |
| Heavy-tailed (revenue, latency) | wide bounds | wide bounds | Std is unstable; widen or use MAD |
| Sparse / high-null | N/A | N/A | Use null_fraction first |
