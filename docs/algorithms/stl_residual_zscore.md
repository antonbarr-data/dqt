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

# clean weekly-seasonal signal
trend = np.linspace(100, 110, 120)
seasonal = 10 * np.sin(2 * np.pi * np.arange(120) / 7)
noise = rng.normal(0, 1, 120)
values = trend + seasonal + noise

ref = pd.DataFrame({"metric": values[:90]}, index=dates[:90])
curr = pd.DataFrame({"metric": values[90:].copy()}, index=dates[90:])

# inject a spike on day 95
curr.iloc[5, 0] += 40.0

det = STLAnomalyDetector(period=7)
state = det.fit(ref)
result = det.score(curr, state)
print(result.verdict)        # fail (spike >> 5σ)
print(result.plain_english)  # "Max STL residual Z-score 18.43 (1 anomalous point)"
print(result.score)          # ~18.4
print(result.details["anomaly_count"])  # 1
```

## Reference

- Cleveland, R. B., Cleveland, W. S., McRae, J. E., & Terpenning, I. (1990). STL: A seasonal-trend decomposition procedure based on Loess. *Journal of Official Statistics*, 6(1), 3–73.
- `packages/dqt/src/dqt/algorithms/timeseries/stl.py`

## Tests

`packages/dqt/tests/algorithms/timeseries/test_stl_residual_zscore.py`
