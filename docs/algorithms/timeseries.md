# Time-Series Anomaly Detectors

## STL Residuals (`stl_residual_zscore`)
**Ref:** Cleveland et al. (1990) *JASA* — Seasonal-Trend Decomposition using Loess

Decomposes the series into trend, seasonal, and residual components. Anomalies are residuals with large Z-score relative to the reference residual distribution.

**Assumptions:** Regular time intervals. Seasonal period known (default 7 for daily data with weekly seasonality). Minimum 2 * period + 1 observations.

**Works well when:** Data has a clear seasonal pattern (daily/weekly/annual). Revenue, pageview, event-count metrics.

**Fails when:** Irregular intervals, missing values, or no seasonality. Use Page-Hinkley for non-seasonal data.

**Minimum N:** 100 for fit, 15 for score (2 * period + 1).

```python
from dqt.algorithms.timeseries.stl import STLAnomalyDetector
det = STLAnomalyDetector(period=7)   # 7 for weekly seasonality in daily data
```

## BOCPD (`bocpd`)
**Ref:** Adams & MacKay (2007) arXiv:0710.3742

Bayesian Online Changepoint Detection. Maintains a posterior over run-length (time since last changepoint). Score = max changepoint probability.

**Assumptions:** Normal-inverse-chi-squared conjugate prior. Works best on approximately Gaussian segments.

**Works well when:** Sudden level shifts (deploys, campaigns). Online streaming data.

**Fails when:** Gradual drift (use Wasserstein-1 or ADWIN). Very short series (<30 points).

**hazard_lambda default:** 20 (expected run length = 20 time steps between changepoints). Increase for slower-changing data.

```python
from dqt.algorithms.timeseries.bocpd import BOCPDDetector
det = BOCPDDetector(hazard_lambda=20)    # daily data: 20 steps ≈ 3 weeks between changes
# det = BOCPDDetector(hazard_lambda=200) # hourly data: 200 steps ≈ 8 days between changes
```

## ADWIN (`adwin`)
**Ref:** Bifet & Gavalda (2007) *SDM*

Adaptive Windowing. Scans all cut-points in the combined ref+current stream using Hoeffding's bound. Returns 1.0 if drift detected, 0.0 if stable.

**Assumptions:** Real-valued stream. Uses Hoeffding bound (distribution-free).

**Works well when:** Streaming data, online learning. Sensitive to mean shifts.

**Fails when:** Variance changes only (ADWIN detects mean shifts). Very noisy data with δ too small.

```python
from dqt.algorithms.drift.adwin import ADWINDetector
det = ADWINDetector(delta=0.002)  # 0.002 ≈ 99.8% confidence before alarm
```
