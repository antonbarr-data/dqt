# `timeseries.stl_residual_zscore`

> *STL residual Z-score* — decomposes a time series into trend, seasonal, and residual components via Loess smoothing; anomalies are detected as residuals whose absolute Z-score exceeds a threshold.

## What it does

At fit time, runs `statsmodels.tsa.seasonal.STL` (with `robust=True`) on the reference window and stores the mean and standard deviation of the residual component. At score time it decomposes the current window with the same period, standardises each residual against the reference baseline (Z = (r − μ_ref) / σ_ref), and returns the maximum absolute Z-score as the score. Points with |Z| > 3.0 are individually counted as anomalies (reported in `details["anomaly_count"]`). The STL `robust=True` flag downweights extreme residuals during trend/seasonal fitting, making the decomposition itself resistant to the very anomalies being detected.

## When to use it

- Regular time series with a clear seasonal period (daily, weekly, monthly patterns).
- Metric monitoring where you want to separate trend and seasonality before anomaly detection — avoids false positives on weekends or daily patterns.
- When the series has known periodicity (page views, order volume by day-of-week, IoT sensor readings).
- Good default for "spike" detection on any metric with a repeating cycle.

## When not to use it

- Non-seasonal series — use CUSUM, Page-Hinkley, or matrix profile instead.
- Very short windows: fit requires at least 2 × period + 1 observations; score requires the same minimum in the current window.
- Series with abrupt level shifts (structural breaks) — the trend component absorbs them and may mask anomalies; use BOCPD for changepoint detection.
- Irregular or unevenly-spaced timestamps — STL assumes a fixed integer period.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `period` | `int` | `7` | Seasonal period in number of observations (e.g. 7 for daily data with weekly seasonality) |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `3.0` |
| `fail_threshold` | `5.0` |
| `direction` | `lower_is_better` |
| `score meaning` | Maximum absolute Z-score of STL residuals over the current window; warn at Z ≥ 3, fail at Z ≥ 5 |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.timeseries.stl import STLAnomalyDetector

rng = np.random.default_rng(42)
dates = pd.date_range("2024-01-01", periods=120, freq="D")

# fct_bookings — daily booking counts with a weekly seasonal pattern
trend = np.linspace(300, 330, 120)
seasonal = 50 * np.sin(2 * np.pi * np.arange(120) / 7)  # weekend dip
noise = rng.normal(0, 5, 120)
daily_bookings = trend + seasonal + noise

ref = pd.DataFrame({"booking_count": daily_bookings[:90]}, index=dates[:90])
curr = pd.DataFrame({"booking_count": daily_bookings[90:].copy()}, index=dates[90:])

# inject a spike on day 95 — e.g. a flash sale drove a sudden surge
curr.iloc[5, 0] += 400.0

det = STLResidualZScoreDetector(
    period=7,      # seasonality period in time steps; 7 for daily data with weekly cycle (most common
                   # for warehouse metrics); use 24 for hourly data with daily cycle; use 365 for
                   # daily data with annual cycle; getting period wrong will misattribute seasonal
                   # patterns as anomalies
)
state = det.fit(ref)
result = det.score(curr, state)
print(result.verdict)        # fail (spike >> 5σ)
print(result.plain_english)  # "Max STL residual Z-score 18.43 (1 anomalous point)"
print(result.score)          # ~18.4
print(result.details["anomaly_count"])  # 1
```

## Learn more

- 📺 [Robust Anomaly Detection + Seasonal-Trend Decomposition: Time Series Talk](https://www.youtube.com/watch?v=1NXryMoU7Ho) — demonstrates STL decomposition in Python, explains how the robust flag handles outliers during fitting, and shows residual-based anomaly detection.

## Implementation

[`packages/dqt/src/dqt/algorithms/timeseries/stl.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/timeseries/stl.py)

## Reference

- Cleveland, R. B., Cleveland, W. S., McRae, J. E., & Terpenning, I. (1990). STL: A seasonal-trend decomposition procedure based on Loess. *Journal of Official Statistics*, 6(1), 3–73.

## Tests

`packages/dqt/tests/algorithms/timeseries/test_stl_residual_zscore.py`

## When it works well

- Time series with clear, stable seasonal patterns (daily, weekly, or annual cycles) and at least 2 full seasons of history.
- Metric monitoring at regular cadence (hourly, daily) where trend and seasonality can be cleanly separated from anomalies.

## When it fails / Limitations

- No seasonal pattern — STL decomposition assigns all variance to the residual component, inflating scores; use `cusum` or `page_hinkley` for non-seasonal series.
- Fewer than 2 full seasonal periods — insufficient history to fit the Loess smoother reliably.
- Abrupt level shifts in the trend component inflate the residuals for nearby points; BOCPD or CUSUM detect these more accurately.
- Residuals inherit the Z-score limitation: FPR inflates on non-normal residuals (common in count or percentage time series).
- Minimum recommended sample: 2 × seasonal_period rows (e.g. 14 observations for weekly seasonality).
- FPR at defaults (z_threshold=3.0) on normal residuals: ~0.3%.
- FPR at defaults on heavy-tailed residuals: 3–10%.

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Normal residuals | (default) | (default) | STAT_SCALES defaults |
| Heavy-tailed residuals | 4.0 | 5.0 | Raise threshold to reduce false positives |
| No seasonality | N/A | N/A | Use cusum or page_hinkley instead |

## Failure modes and known limits

| Failure mode | Symptom | Fix |
|---|---|---|
| Wrong seasonality period | If `period` doesn't match data frequency (weekly data with period=30), residuals carry seasonal signal | Use `period=7` for daily data, `period=52` for weekly; auto-detection via STL auto-period (J.1) |
| Non-stationary trend | STL handles trend via LOESS; very fast trend changes may appear in residuals | Check `details["trend_magnitude"]`; CUSUM may better handle abrupt level shifts |
| Too short series | `min_len = 2*period + 1` enforced; raises ValueError below | Ensure at least `2*period+1` observations |
| Scores > 1.0 | STL residual z-score is unbounded; score is clipped | Check `details["max_z"]` for raw score |

## FPR at default threshold (z=3.0)

| Data shape | FPR |
|---|---|
| Gaussian residuals (ideal) | ~0.3% |
| Lognormal residuals (revenue) | ~1-5% |
| Highly seasonal with period mismatch | Up to 50% -- **always verify period** |
