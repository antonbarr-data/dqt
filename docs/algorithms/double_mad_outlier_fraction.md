# `outliers_uni.double_mad_outlier_fraction`

> *Outlier fraction (double-MAD)* — flags the fraction of outliers using an asymmetric MAD that applies separate scale estimates to the left and right sides of the median, making it robust on skewed distributions.

## What it does

Extends the modified Z-score approach by computing two MADs: `MAD_left` (median of |xi − median| for values at or below the median) and `MAD_right` (for values at or above the median). At `score` time, each value's modified Z-score uses the side-appropriate MAD — `MAD_left` for values below the median, `MAD_right` for values above it. Multiplying by the consistency factor `0.6745` preserves the interpretation of the threshold in standard-deviation units. The reference `fit` step records the median and both half-MADs from the baseline window; `score` computes the fraction of current values exceeding `threshold`.

## When to use it

- Numeric columns with a skewed or asymmetric distribution (e.g. transaction amounts, latencies, file sizes).
- When the right tail is much heavier than the left (or vice versa) and a symmetric MAD would inflate the threshold on the lighter side.
- Preferred over `adjusted_boxplot_fraction` when medcouple exceeds 0.5 or skewness exceeds 2.0 (auto-selected by `auto_outlier`).
- When breakdown-point robustness (50%) is required alongside asymmetric sensitivity.

## When not to use it

- Symmetric or near-normal data — plain `mad_outlier_fraction` is sufficient and slightly more efficient.
- Distributions with so few values below (or above) the median that `MAD_left` or `MAD_right` is estimated from fewer than ~10 points.
- Categorical or ordinal columns where the concept of side-specific deviation is not meaningful.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `threshold` | `float` | `6.5` | Modified Z-score cutoff. Values on either side whose side-adjusted modified Z exceeds this are counted as outliers. Default 6.5 is calibrated for lognormal(0,1) revenue data. Use 3.5 for near-Gaussian data. |

## Calibration by data shape

Default threshold=6.5 was calibrated on lognormal(0,1) data (revenue shape).
Iglewicz & Hoaglin's original threshold=3.5 targets near-Gaussian data.
Use 3.5 for Gaussian KPIs; use 6.5 for heavy-tailed or skewed distributions.

| Shape | FPR at threshold=6.5 |
|---|---|
| lognormal(0,1) — revenue | 1.040% (calibrated target) |
| normal(0,1) — Gaussian | 0.000% (very conservative — use 3.5) |
| poisson(λ=10) — count | 0.000% |
| beta(0.5,0.5) — ratio | 0.000% |
| pareto(1.5) — heavy-tail | 2.880% |
| exponential(λ=1) | 0.060% |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.01` (1%) |
| `fail_threshold` | `0.05` (5%) |
| `direction` | `lower_is_better` |
| `score meaning` | Fraction of values flagged by the asymmetric double-MAD rule (0 = no outliers, 0.20 = scale max) |

## Example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore
from dqt.adapters.duckdb import DuckDBAdapter

# fct_gigs.price_usd — right-skewed gig prices with a high-end anomaly
df = pd.DataFrame({
    "price_usd": [25, 30, 28, 32, 27, 29, 31, 26, 30, 5000]  # 5000 is the spike
})
adapter = DuckDBAdapter.from_dataframe(df)

check = Check(
    schema_name="main",
    table_name="fct_gigs",
    column_name="price_usd",
    detector_slug="double_mad_outlier_fraction",
    detector_params={
        "threshold": 3.5,  # same scale as symmetric MAD; 3.5 works well for most skewed
                           # columns; lower only the relevant side's threshold when one tail
                           # matters more (e.g. only care about high prices → lower to 2.5)
    },
)
result = Runner(MemoryStore()).run(check, adapter)
print(result.verdict)         # pass / warn / fail
print(result.plain_english)   # human-readable explanation
print(result.score)           # raw score
```

## Learn more

- 📺 [How Is MAD Used To Detect Outliers? — The Friendly Statistician](https://www.youtube.com/watch?v=8WbvTy6XwG4) — covers MAD-based outlier detection including the double-MAD extension for asymmetric distributions.

## Implementation

[`packages/dqt/src/dqt/algorithms/outliers_uni/mad.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/outliers_uni/mad.py)

## Reference

- Rousseeuw, P.J. & Croux, C. (1993). *Alternatives to the Median Absolute Deviation*. Journal of the American Statistical Association, 88(424), 1273–1283.
- Leys, C. et al. (2013). *Detecting outliers: Do not use standard deviation around the mean, use absolute deviation around the median*. Journal of Experimental Social Psychology, 49(4), 764–766.
- `packages/dqt/src/dqt/algorithms/outliers_uni/mad.py`

## Tests

`packages/dqt/tests/algorithms/outliers_uni/test_double_mad_outlier_fraction.py`

## When it works well

- Asymmetrically skewed numeric columns (revenue, file sizes, time-to-event) where right-tail outliers should be treated differently from left-tail outliers.
- Uses separate MAD estimates above and below the median, providing asymmetric fences that respect the column's natural skewness.

## When it fails / Limitations

- Very small samples (< 20 rows per side) make the per-side MAD estimates unreliable.
- Bimodal distributions can cause one side's MAD to span both modes, inflating or deflating the threshold.
- When one side has MAD = 0 (e.g. many values at the same boundary), that side's threshold is undefined; the implementation adds an epsilon.
- Minimum recommended sample: 20 rows.
- FPR at defaults (threshold=3.5) on clean normal data: ~0.3%.
- FPR at defaults on heavy-tailed data: ~0.5–1%.

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Normal | (default) | (default) | STAT_SCALES defaults |
| Heavy-tailed (revenue, latency) | (default) | (default) | Asymmetric MAD handles this |
| Sparse / high-null | N/A | N/A | Use null_fraction first |
