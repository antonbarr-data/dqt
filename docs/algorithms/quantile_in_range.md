# `basic.quantile_in_range`

> *Quantile in bounds* — 1.0 if the specified quantile falls outside `[min_val, max_val]`; 0.0 otherwise.

## What it checks

Computes `PERCENTILE_CONT(q) WITHIN GROUP (ORDER BY col)` and tests whether it is within the declared bounds. Returns a binary score: 0.0 (pass) if in range, 1.0 (fail) otherwise. No baseline is needed. Useful for SLA checks like "p95 response time must stay below 2 seconds".

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `quantile` | `float` | `0.95` | Quantile to compute, in `(0, 1]` |
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
from dqt.algorithms.basic.numeric_bounds import QuantileInRangeDetector

# QuantileInRangeDetector(
#     quantile=0.95,          # 0.95 (p95) is the most common choice for one-sided upper-tail checks;
#                             # use 0.99 for stricter tail monitoring;
#                             # use 0.50 for a robust median check
#     min_val=0.0,            # lower bound (rarely needed for tail checks)
#     max_val=float("inf"),   # maximum acceptable value at that quantile
# )

check = Check(
    schema_name="public",
    table_name="api_requests",
    column_name="response_ms",
    detector_slug="quantile_in_range",
    params={"quantile": 0.95, "min_val": 0.0, "max_val": 2000.0},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / fail
```

## Compatible with

- Great Expectations: `expect_column_quantile_values_to_be_between`
- Soda: `percentile` (with threshold)

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py`

## When it works well

- Monitoring percentile-based SLAs (e.g. p95 latency < 500ms, p99 order value < $10,000).
- More robust than `max_in_range` for heavy-tailed columns because extreme individual values don't move high percentiles significantly.

## When it fails / Limitations

- Requires choosing the quantile level — wrong choice misses the intended anomaly (e.g. p50 instead of p99 for tail-latency monitoring).
- Quantile estimates at extreme percentiles (p99.9, p0.1) require large samples to be reliable.
- FPR at defaults: 0% (rule-based).
- Minimum recommended sample: 1/(1-p) rows for the quantile level p (e.g. 100 rows for p99).
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based; but bounds should account for heavy tails).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Normal bounded | calibrated bounds | calibrated bounds | Derive from reference window |
| Heavy-tailed (revenue, latency) | calibrated bounds | calibrated bounds | Use p95/p99 for tail monitoring |
| Sparse / high-null | N/A | N/A | Use null_fraction first |

## Failure modes and known limits

`quantile_in_range` is deterministic given the quantile estimate. The quantile estimator itself (PERCENTILE_CONT) is stable for moderate to large N but can fluctuate significantly for extreme quantiles (p99.9, p0.1) on small samples.

| Failure mode | Symptom | Fix |
|---|---|---|
| Insufficient N for extreme quantile | p99 requires ~100 rows; p99.9 requires ~1000 rows; on small tables the estimate is unreliable | Use a quantile no more extreme than 1/(0.1 * N); e.g. for N=200 use at most p95 |
| Wrong quantile direction | Monitoring p5 (lower tail) instead of p95 (upper tail) misses the intended SLA | Verify the quantile level matches the business SLA direction |
| Seasonal quantile drift | p95 latency is higher at peak hours; static bounds fire during expected peaks | Set bounds from the 90-day percentile-of-the-quantile to capture seasonal variation |
| Heavy-tailed column (Pareto-like) | p95 varies widely run-to-run because extreme values dominate | Use a wider bound derived from the 30-day reference max of the quantile value |
| Stale bounds after load change | Query volume doubles; p95 latency increases legitimately | Re-calibrate bounds after any planned load change |
| PERCENTILE_CONT interpolation difference | Different warehouses interpolate PERCENTILE_CONT differently at the same quantile level | Verify the warehouse's interpolation method; use PERCENTILE_DISC for discrete columns |

### FPR table

| Data shape | Expected FPR (correct bounds) | Notes |
|---|---|---|
| Normal(0,1), p95, bounds calibrated from 30d history | ~0% | Quantile is stable for Gaussian data |
| Lognormal(0,2), p95, bounds calibrated from 30d history | ~2-3% | Heavy tail makes p95 more variable |
| Pareto(1.5), p95 | ~5-8% | Quantile at p95 is highly variable for Pareto |

### Threshold recommendations

- For SLA monitoring: set max_val at the SLA limit (e.g. p95 latency <= 500ms) and set min_val=0.
- For anomaly detection on quantile drift: derive bounds from the historical min/max of the quantile statistic over the reference window, not from the raw data range.
- Use at least N >= 100 / (1 - quantile) rows per window for reliable quantile estimation.
