# `outliers_uni.zscore_outlier_fraction`

> *Outlier fraction (Z-score)* — flags the fraction of values whose standard Z-score exceeds a threshold; valid only when the column follows an approximately normal distribution.

## What it does

Computes the standard Z-score for each value: `|xi − mean| / std`. The `fit` step records the sample mean and standard deviation (ddof=1) from the reference window. At `score` time, the fraction of current values whose absolute Z-score exceeds `threshold` is returned as the score. The method assumes the baseline is normally distributed; under that assumption, a threshold of 3.0 corresponds to flagging values beyond the 99.7th percentile (the three-sigma rule).

## When to use it

- Numeric columns that have been confirmed (or reasonably assumed) to be normally distributed.
- When you want a simple, explainable rule that maps directly to standard deviations from the mean.
- When sample sizes are large (n ≥ 30) and the distribution is verified as approximately Gaussian.
- Auto-selected by `auto_outlier` when the reference distribution is classified as normal.

## When not to use it

- Heavy-tailed distributions (e.g. Pareto, log-normal, financial returns) — the inflated standard deviation causes systematic under-detection; use `mad_outlier_fraction` instead.
- Skewed distributions — the asymmetric tails cause different false-positive rates on each side; use `double_mad_outlier_fraction` or `adjusted_boxplot_fraction` instead.
- Contaminated reference data — even a single high outlier in the reference inflates the mean and std, masking other outliers (masking effect). MAD-based methods have a 50% breakdown point; Z-score has 0%.
- Small samples (n < 30) — the sample mean and std are too noisy; consider `grubbs` for single-outlier detection.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `threshold` | `float` | `3.0` | Z-score cutoff. Values with |Z| above this are counted as outliers. A value of 3.0 corresponds to the three-sigma rule; 2.5 is more sensitive. |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.01` (1%) |
| `fail_threshold` | `0.05` (5%) |
| `direction` | `lower_is_better` |
| `score meaning` | Fraction of values with |Z| > `threshold` (0 = no outliers, 0.10 = scale max) |

## Example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore
from dqt.adapters.duckdb import DuckDBAdapter

# fct_gigs.price_usd — spike detection on near-normally distributed gig prices
df = pd.DataFrame({
    "price_usd": [25, 30, 28, 32, 27, 29, 31, 26, 30, 500]  # 500 is the spike
})
adapter = DuckDBAdapter.from_dataframe(df)

check = Check(
    schema_name="main",
    table_name="fct_gigs",
    column_name="price_usd",
    detector_slug="zscore_outlier_fraction",
)
result = Runner(MemoryStore()).run(check, adapter)
print(result.verdict)         # pass / warn / fail
print(result.plain_english)   # human-readable explanation
print(result.score)           # raw score
```

## Learn more

- 📺 [How to Detect Outliers with Z Score | Clearly Explained](https://www.youtube.com/watch?v=Qv2vCviL4iU) — step-by-step walkthrough of the Z-score formula, the three-sigma rule, and when it fails on non-normal data.

## Reference

- Press, W.H. et al. (1992). *Numerical Recipes in C* (2nd ed.), Section 14.1. Cambridge University Press. (Standard Z-score derivation.)
- `packages/dqt/src/dqt/algorithms/outliers_uni/zscore.py`

## Tests

`packages/dqt/tests/algorithms/outliers_uni/test_zscore_outlier_fraction.py`
