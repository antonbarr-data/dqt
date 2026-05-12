# `outliers_uni.mad_outlier_fraction`

> *Outlier fraction (MAD)* — flags the fraction of values whose modified Z-score exceeds a threshold, using the Median Absolute Deviation as a robust scale estimator.

## What it does

Computes a modified Z-score for each value: `|xi − median| × 0.6745 / MAD`, where `0.6745` is the consistency factor that makes MAD an asymptotically consistent estimator of σ under normality. The reference `fit` step records the median and MAD from the baseline window. At `score` time, the fraction of current values whose modified Z-score exceeds `threshold` is returned as the score. Because MAD is resistant to masking by multiple outliers, it remains reliable even when 25–30% of the data is contaminated.

## When to use it

- Numeric columns with a unimodal, roughly symmetric distribution that may be heavy-tailed.
- When the dataset may already contain outliers that would inflate the mean and standard deviation (breakdown point 50%).
- When sample sizes are moderate to large (n ≥ 30).
- Default fallback for `auto_outlier` when the distribution is classified as heavy-tailed, multimodal, or unknown.

## When not to use it

- Strictly normal data with no heavy tails — `zscore_outlier_fraction` is lower-variance and better calibrated there.
- Strongly skewed distributions — use `double_mad_outlier_fraction` instead, which applies separate MADs to each side of the median.
- Very small samples (n < 10) — the sample MAD estimate is noisy; consider `grubbs` for single-outlier detection.
- Categorical or sparse-integer columns where median and MAD are not meaningful.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `threshold` | `float` | `11.0` | Modified Z-score cutoff. Values above this are counted as outliers. Default 11.0 is calibrated for lognormal(0,1) revenue data. Use 3.5 for near-Gaussian data; 2.5 for stricter alerting. |

## Calibration by data shape

Default threshold=11.0 was calibrated on lognormal(0,1) data (revenue shape).
Iglewicz & Hoaglin's original threshold=3.5 targets near-Gaussian data.
Use 3.5 for Gaussian KPIs; use 11.0 for heavy-tailed distributions.

| Shape | FPR at threshold=11.0 |
|---|---|
| lognormal(0,1) — revenue | 1.060% (calibrated target) |
| normal(0,1) — Gaussian | 0.000% (very conservative — use 3.5) |
| poisson(λ=10) — count | 0.000% |
| beta(0.5,0.5) — ratio | 0.000% |
| pareto(1.5) — heavy-tail | 3.520% |
| exponential(λ=1) | 0.020% |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.01` (1%) |
| `fail_threshold` | `0.05` (5%) |
| `direction` | `lower_is_better` |
| `score meaning` | Fraction of values with modified Z-score > `threshold` (0 = no outliers, 0.20 = scale max) |

## Example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore
from dqt.adapters.duckdb import DuckDBAdapter

# fct_gigs.price_usd — detect pricing anomalies on the Gigler marketplace
df = pd.DataFrame({
    "price_usd": [25, 30, 28, 32, 27, 29, 31, 26, 30, 999]  # 999 is the spike
})
adapter = DuckDBAdapter.from_dataframe(df)

check = Check(
    schema_name="main",
    table_name="fct_gigs",
    column_name="price_usd",
    detector_slug="mad_outlier_fraction",
    detector_params={
        "threshold": 3.5,  # Leys et al. recommended default; raise to 4–5 on heavy-tailed
                           # columns (e.g. payment amounts) to cut false positives; lower to
                           # 2.5–3.0 for stricter alerting on tightly-controlled columns
    },
)
result = Runner(MemoryStore()).run(check, adapter)
print(result.verdict)         # pass / warn / fail
print(result.plain_english)   # human-readable explanation
print(result.score)           # raw score
```

## Learn more

- 📺 [How Is MAD Used To Detect Outliers? — The Friendly Statistician](https://www.youtube.com/watch?v=8WbvTy6XwG4) — walks through the modified Z-score formula using MAD and shows why it outperforms standard deviation for heavy-tailed data.

## Implementation

[`packages/dqt/src/dqt/algorithms/outliers_uni/mad.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/outliers_uni/mad.py)

## Reference

- Leys, C. et al. (2013). *Detecting outliers: Do not use standard deviation around the mean, use absolute deviation around the median*. Journal of Experimental Social Psychology, 49(4), 764–766.
- `packages/dqt/src/dqt/algorithms/outliers_uni/mad.py`

## Tests

`packages/dqt/tests/algorithms/outliers_uni/test_mad_outlier_fraction.py`

## When it works well

- Numeric columns with any unimodal distribution including heavy-tailed and skewed data (revenue, latency, duration).
- 50% breakdown point — the median and MAD are unaffected by up to half the data being contaminated.

## When it fails / Limitations

- Bimodal or multimodal distributions produce an inflated MAD (or near-zero MAD if modes are close), causing missed detections or constant false positives.
- When MAD = 0 (more than 50% of values are identical), the modified Z-score is undefined; the implementation falls back to a small epsilon to avoid division by zero, but results are unreliable.
- Less powerful than Z-score for detecting mild outliers in genuinely normal data.
- Minimum recommended sample: 10 rows for stable MAD estimates.
- FPR at defaults (threshold=3.5) on clean normal data: ~0.3%.
- FPR at defaults on heavy-tailed data: ~0.5–1%.

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Normal | (default) | (default) | STAT_SCALES defaults |
| Heavy-tailed (revenue, latency) | (default) | (default) | MAD is robust; defaults hold |
| Sparse / high-null | N/A | N/A | Use null_fraction first |
