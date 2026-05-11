# `outliers_uni.outlier_fraction_drift`

> *Outlier fraction drift* — a meta-detector that tracks the outlier fraction produced by an upstream detector over time and alerts when it deviates outside its learned historical range.

## What it does

This detector operates on a time series of outlier fractions rather than raw data. At fit time it receives a DataFrame with a single column `"outlier_fraction"` containing the historical run-by-run outlier fractions from an upstream detector (e.g. `mad_outlier_fraction` or `iqr_fence`). It computes a tolerance range via IQR, percentile, or z-score method and stores the `[lower, upper]` bounds. At score time it receives the current period's outlier fraction and computes a deviation score: `0.0` if within range, or `(deviation from nearest bound) / range_width` if outside, capped at `1.0`. This lets you alert not just when individual values are outliers, but when the *rate* of outliers itself has changed.

## When to use it

- Long-running pipelines where you care about outlier rate stability: a sudden jump in the IQR-flagged fraction of `price_usd` rows is a signal in its own right.
- Catching slow-burn degradation: if the outlier fraction is creeping up gradually, this detector triggers before any single-window outlier threshold fires.
- Pairing with any upstream univariate outlier detector to add a meta-monitoring layer without duplicating threshold logic.
- Governance use case: ensure that the fraction of out-of-range values in `fct_gigs.price_usd` stays within SLA bounds across all daily runs.

## When not to use it

- Requires at least 3 historical data points to fit — cannot be used on the very first run or after a pipeline reset.
- Not suitable for detecting individual row-level outliers — use the upstream detector directly for that.
- When the upstream outlier fraction has high natural variance (seasonal peaks, weekends), the IQR range may be wide and miss real anomalies; consider `method="percentile"` with narrow bounds or use `adwin` on the fraction time series instead.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `method` | `str` | `"iqr"` | Range estimation method. `"iqr"` = Tukey fences (Q1 − k×IQR, Q3 + k×IQR). `"percentile"` = explicit lower/upper percentile bounds. `"zscore"` = mean ± k×std. |
| `k` | `float` | `1.5` | IQR multiplier (for `method="iqr"`) or z-score threshold (for `method="zscore"`). |
| `lower_pct` | `float` | `5.0` | Lower percentile bound, only used when `method="percentile"`. |
| `upper_pct` | `float` | `95.0` | Upper percentile bound, only used when `method="percentile"`. |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.001` |
| `fail_threshold` | `0.01` |
| `direction` | `lower_is_better` |
| `score meaning` | Normalised deviation from the historical range; `0.0` = within range; `> 0` = distance outside bounds divided by range width; warn at any deviation > 0.001 |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.outliers_uni.outlier_fraction_range import OutlierFractionRangeDetector

rng = np.random.default_rng(42)

# Historical outlier fractions from an upstream IQR detector on fct_gigs.price_usd (90 days)
historical_fractions = rng.normal(loc=0.02, scale=0.003, size=90).clip(0, 1)
ref = pd.DataFrame({"outlier_fraction": historical_fractions})

# Today: outlier fraction normal
curr_ok   = pd.DataFrame({"outlier_fraction": [0.021]})
# Today: outlier fraction spiked — possible data quality incident
curr_high = pd.DataFrame({"outlier_fraction": [0.12]})

det = OutlierFractionRangeDetector()
state = det.fit(ref, method="iqr", k=1.5)

result_ok = det.score(curr_ok, state)
print(result_ok.verdict)   # pass
print(result_ok.score)     # 0.0

result_high = det.score(curr_high, state)
print(result_high.verdict)        # fail
print(result_high.plain_english)  # "Outlier fraction 0.120 is outside expected range [0.011, 0.029] (drift score 1.0000)"
```

## Learn more

<!-- TODO: no simple YouTube explanation found -->

## Reference

- Tukey, J.W. (1977). *Exploratory Data Analysis*. Addison-Wesley. (IQR fences as the canonical univariate range method.)
- `packages/dqt/src/dqt/algorithms/outliers_uni/outlier_fraction_range.py`

## Tests

`packages/dqt/tests/algorithms/outliers_uni/test_outlier_fraction_drift.py`
