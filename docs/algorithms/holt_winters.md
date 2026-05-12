# `timeseries.holt_winters`

> *Anomaly fraction (HW)* — fits an additive Holt-Winters exponential smoothing model on the reference window and flags current values that fall outside the model's prediction interval.

## What it does

At fit time, trains `statsmodels.tsa.holtwinters.ExponentialSmoothing` with additive trend and additive seasonality using full optimisation of the smoothing parameters. The residuals from the fitted model are stored; their standard deviation becomes the basis of the prediction interval. At score time, the model forecasts n steps ahead (where n = len(current)) and constructs a symmetric interval of width ±z × σ_resid, where z is the normal quantile for the configured coverage level (default 99%). The score is the fraction of current values that fall outside the interval — so a score of 0.05 means 5% of observations are anomalous. Requires at least 2 × period observations in the reference window.

## When to use it

- Weekly-seasonal metrics: daily session counts, daily booking volume, daily active sellers — any series with a clear repeating cycle.
- When you want a model that explicitly represents trend + seasonality before anomaly detection, avoiding false positives on routine weekly dips.
- Medium-length reference windows (14–90 days for daily data) — Holt-Winters is well-calibrated in this range.
- As a lower-complexity alternative to Prophet when holiday calendars and external regressors are not needed.

## When not to use it

- Series without a clear seasonal period — use CUSUM, Page-Hinkley, or STL residual score instead.
- Reference windows shorter than 2 × period — the model cannot initialise; the detector raises `ValueError`.
- Multiple overlapping seasonalities (e.g. daily + weekly + annual) — Prophet or TBATS handles those better.
- High-frequency data (minute-level) where the period would be hundreds of observations — fitting cost scales with series length; consider downsampling or STL.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `period` | `int` | `7` | Seasonal period in observations. Use 7 for daily data with weekly seasonality, 24 for hourly data with daily seasonality. |
| `alpha` | `float` | `0.99` | Coverage for the prediction interval (e.g. 0.99 = 99% PI). A value outside this interval counts as an anomaly. |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.05` |
| `fail_threshold` | `0.10` |
| `direction` | `lower_is_better` |
| `score meaning` | Fraction of current values outside the Holt-Winters prediction interval; warn when ≥ 5%, fail when ≥ 10% |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.timeseries.holt_winters import HoltWintersDetector

rng = np.random.default_rng(7)
dates = pd.date_range("2024-01-01", periods=120, freq="D")

# fct_sessions: daily session count with weekly seasonality
dow_effect = np.tile([1.0, 0.9, 0.85, 0.88, 1.0, 1.3, 1.2], 18)[:120]
trend = np.linspace(5000, 5400, 120)
noise = rng.normal(0, 120, 120)
sessions = trend * dow_effect + noise

ref = pd.DataFrame({"sessions": sessions[:90]}, index=dates[:90])
curr = pd.DataFrame({"sessions": sessions[90:].copy()}, index=dates[90:])

# inject anomaly: a 4-day outage that suppresses sessions
curr.iloc[3:7, 0] *= 0.30

det = HoltWintersDetector(
    period=7,     # seasonality period in observations; same convention as STL: 7 for daily data
                  # with weekly cycle, 24 for hourly data with daily cycle; must be consistent with
                  # the reference window length (≥ 2 × period)
    alpha=0.99,   # level smoothing factor; 0.99 means the forecast trusts recent data almost
                  # entirely (fast adaptation); lower to 0.7–0.9 for smoother forecasts that are
                  # less reactive to single-day spikes
)
state = det.fit(ref)
result = det.score(curr, state)

print(result.verdict)        # fail — 4 days anomalous out of 30
print(result.score)          # ~0.13 (13% of values outside PI)
print(result.plain_english)  # "4 of 30 current values outside 99% Holt-Winters prediction interval (13.3%)"
print(result.details["n_anomalies"])  # 4
```

## Learn more

- 📺 [TSA — Exponential Smoothing — Trend and/or Seasonality (Holt Winters) — YouTube](https://www.youtube.com/watch?v=vQCcD0j-vHQ) — thorough theory walkthrough of additive and multiplicative Holt-Winters with worked R examples.

## Implementation

[`packages/dqt/src/dqt/algorithms/timeseries/holt_winters.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/timeseries/holt_winters.py)

## Reference

- Holt, C. C. (1957). Forecasting seasonals and trends by exponentially weighted averages. *ONR Memorandum 52*, Carnegie Institute of Technology. (Reprinted in *International Journal of Forecasting* 20(1), 2004.)
- Winters, P. R. (1960). Forecasting sales by exponentially weighted moving averages. *Management Science*, 6(3), 324–342.

## Tests

`packages/dqt/tests/algorithms/timeseries/test_holt_winters.py`

## When it works well

- Time series with clear trend and/or additive/multiplicative seasonality at a known regular cadence (daily, weekly).
- Good for forecasting-based anomaly detection when the series has been stable for at least 2–3 seasonal periods.

## When it fails / Limitations

- Non-seasonal or irregular time series — the seasonal component assumption causes over-smoothing and residuals lose meaning; use `cusum` or `page_hinkley` instead.
- Fewer than 2 full seasonal periods of history — insufficient data to initialise the seasonal component.
- Level shifts in the series confuse the exponential smoothing — the model adapts slowly, producing a streak of false positives after a genuine level change.
- Minimum recommended sample: 2 × seasonal_period rows (e.g. 14 days for weekly seasonality).
- FPR at defaults on stable seasonal data: ~2–5%.
- FPR at defaults on non-seasonal or heavy-tailed data: 10–20%.

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Stable seasonal | (default) | (default) | STAT_SCALES defaults |
| Non-seasonal | N/A | N/A | Use cusum or page_hinkley instead |
| Highly irregular | N/A | N/A | Use bocpd for structural breaks |
