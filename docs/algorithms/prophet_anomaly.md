# `timeseries.prophet_anomaly`

> *Anomaly fraction (Prophet)* — fits Meta's Prophet model on the reference window and flags current values falling outside its uncertainty interval; requires the optional `dqt[forecast]` extra.

## What it does

At fit time, trains a Prophet model on the reference time series (using an internally-generated daily date index). The model captures trend, weekly seasonality, and yearly seasonality automatically. Prophet's `interval_width` parameter controls the width of the uncertainty band. At score time, the model forecasts n steps ahead and labels each current value as anomalous if it lies below `yhat_lower` or above `yhat_upper`. The score is the fraction of anomalous values; a score of 0.10 means 10% of current observations are outside the model's expected range.

**Dependency note**: this detector is a stub until `prophet` is installed. Calling `fit` or `score` without it raises `ImportError` with the install hint `pip install 'dqt[forecast]'`. The detector is always registered in the algorithm registry so checks referencing it can be serialised and loaded without the extra installed.

## When to use it

- Long reference windows (90+ days) where Prophet's Fourier-basis seasonality and changepoint priors outperform simpler exponential smoothing.
- Series with strong holiday effects — Prophet supports holiday calendars directly (extend the detector or pass a pre-fitted model).
- When the reference window itself contains level shifts — Prophet's automatic changepoint detection absorbs them gracefully.
- Daily revenue, booking volume, or any business KPI with multi-scale seasonality.

## When not to use it

- Short reference windows (< 2 seasonal cycles) — Prophet's priors dominate and the fit may be unreliable; use Holt-Winters instead.
- Production environments where `prophet` cannot be installed (heavy Stan/PyStan dependency) — use Holt-Winters or STL as lighter alternatives.
- Sub-daily data where fitting cost is prohibitive — Prophet fits a full Stan model at each `fit` call; consider downsampling.
- When the detector must be importable without optional dependencies — the base `dqt` install works fine; only `fit`/`score` calls fail.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `interval_width` | `float` | `0.95` | Width of Prophet's uncertainty interval (e.g. 0.95 = 95% PI). Values outside this interval are counted as anomalies. |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.05` |
| `fail_threshold` | `0.10` |
| `direction` | `lower_is_better` |
| `score meaning` | Fraction of current values outside Prophet's uncertainty interval; warn when ≥ 5%, fail when ≥ 10% |

## Example

```python
# Requires: pip install 'dqt[forecast]'
import pandas as pd
import numpy as np
from dqt.algorithms.timeseries.prophet_anomaly import ProphetAnomalyDetector

rng = np.random.default_rng(13)
dates = pd.date_range("2023-01-01", periods=180, freq="D")

# fct_bookings: daily revenue with weekly seasonality and an upward trend
dow_effect = np.tile([1.0, 0.9, 0.85, 0.88, 1.05, 1.35, 1.25], 26)[:180]
trend = np.linspace(12000, 15000, 180)
noise = rng.normal(0, 400, 180)
revenue = trend * dow_effect + noise

ref = pd.DataFrame({"revenue_usd": revenue[:150]}, index=dates[:150])
curr = pd.DataFrame({"revenue_usd": revenue[150:].copy()}, index=dates[150:])

# Simulate a 5-day revenue anomaly (e.g. payment processor outage)
curr.iloc[2:7, 0] *= 0.40

det = ProphetAnomalyDetector(interval_width=0.95)
state = det.fit(ref)         # ImportError here if prophet is not installed
result = det.score(curr, state)

print(result.verdict)        # fail
print(result.score)          # ~0.17 (5 of 30 days anomalous)
print(result.plain_english)  # "5 of 30 values outside Prophet 95% uncertainty interval (16.7%)"
```

## Learn more

- 📺 [Time Series Anomaly Detection Using Prophet in Python | Machine Learning — YouTube](https://www.youtube.com/watch?v=viMgmLzYP3g) — step-by-step walkthrough of fitting Prophet and extracting anomalies from its uncertainty bands in Python.

## Reference

- Taylor, S. J., & Letham, B. (2018). Forecasting at scale. *The American Statistician*, 72(1), 37–45.
- `packages/dqt/src/dqt/algorithms/timeseries/prophet_anomaly.py`

## Tests

`packages/dqt/tests/algorithms/timeseries/test_prophet_anomaly.py`
