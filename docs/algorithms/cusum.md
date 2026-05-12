# `timeseries.cusum`

> *CUSUM alarm level* — accumulates standardised deviations from the reference mean to detect persistent upward or downward shifts that would be invisible to a single-point test.

## What it does

At fit time, computes the reference mean (μ) and standard deviation (σ) from the first column of the reference DataFrame. At score time it runs the two-sided CUSUM recurrence: S_hi[t] = max(0, S_hi[t−1] + (x[t]−μ)/σ − k) and S_lo[t] = min(0, S_lo[t−1] + (x[t]−μ)/σ + k), where k is the allowance parameter (half the smallest shift worth detecting, in σ units). The raw alarm statistic is max(S_hi[−1], −S_lo[−1]); the reported score is that value divided by the decision threshold h, so a score ≥ 1.0 means the chart has triggered. Because deviations accumulate across observations, CUSUM catches slow mean drifts far earlier than Shewhart-style single-point rules.

## When to use it

- Monitoring a numeric metric (row count, daily revenue, p99 latency) for a sustained mean shift.
- When false-alarm rate must be tightly controlled — the h parameter maps directly to average run length.
- Sequential/streaming data where new observations arrive one at a time and you want online alerting.
- Complementary to STL: use STL for seasonal anomalies, CUSUM for level shifts on de-seasonalised series.

## When not to use it

- Point spikes that immediately revert — a single large outlier inflates S_hi but the chart resets; use `stl_residual_zscore` or `generalized_esd` instead.
- Non-stationary reference windows (trend present) — detrend first or use BOCPD, which models changing regimes explicitly.
- Categorical or multi-dimensional data — CUSUM is univariate numeric only.
- Very heavy-tailed distributions where σ is a poor spread estimate; consider robust normalisation with MAD before feeding the series to CUSUM.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `k` | `float` | `0.5` | Allowance (slack) in σ units; half the minimum shift worth detecting. Larger k → fewer false alarms, slower detection of small shifts. |
| `h` | `float` | `50.0` | Decision threshold in σ-accumulated units. Score is normalised by h, so score = 1.0 marks the alarm boundary. Tune via ARL tables (Page 1954). |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `1.0` |
| `fail_threshold` | `2.0` |
| `direction` | `lower_is_better` |
| `score meaning` | Normalised CUSUM statistic max(S_hi, −S_lo) / h; score ≥ 1.0 means the chart has triggered (moderate shift), ≥ 2.0 indicates a large or sustained shift |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.timeseries.cusum import CUSUMDetector

rng = np.random.default_rng(42)
dates = pd.date_range("2024-01-01", periods=120, freq="D")

# Simulate daily booking count on fct_bookings — stable baseline then a persistent drop
baseline = rng.poisson(lam=350, size=90).astype(float)
dropped = rng.poisson(lam=290, size=30).astype(float)   # ~17% drop in volume

ref = pd.DataFrame({"bookings": baseline}, index=dates[:90])
curr = pd.DataFrame({"bookings": dropped}, index=dates[90:])

det = CUSUMDetector(
    k=0.5,    # allowable slack in units of σ; 0.5σ means shifts smaller than half a standard
              # deviation are tolerated; lower to 0.25 for very sensitive monitoring, raise to 1.0
              # to ignore small fluctuations
    h=50.0,   # decision threshold (cumulative sum must exceed h to trigger); 50.0 is moderate —
              # lower to 20–30 for earlier detection of small shifts, raise to 100+ for noisy series
)
state = det.fit(ref)
result = det.score(curr, state)

print(result.verdict)        # fail — sustained downward drift detected
print(result.score)          # > 1.0 (alarm level exceeded)
print(result.plain_english)  # "CUSUM alarm level = 1.34 (alarm; S_hi=0.00, S_lo=-67.12)"
print(result.details)        # {"cusum_hi": 0.0, "cusum_lo": -67.12, "ref_mean": 350.x, ...}
```

## Learn more

- 📺 [Time-Weighted Control Charts Explained | CUSUM & EWMA for Precision Monitoring — YouTube](https://www.youtube.com/watch?v=55gGq0DsZ8s) — explains how CUSUM accumulates small process shifts that Shewhart charts miss, with worked examples.

## Implementation

[`packages/dqt/src/dqt/algorithms/timeseries/cusum.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/timeseries/cusum.py)

## Reference

- Page, E. S. (1954). Continuous inspection schemes. *Biometrika*, 41(1–2), 100–115.

## Tests

`packages/dqt/tests/algorithms/timeseries/test_cusum.py`

## When it works well

- Time series monitoring where you need to detect an abrupt, sustained mean shift as quickly as possible (minimise detection delay).
- Works on any numeric time series without seasonal or trend requirements.

## When it fails / Limitations

- Gradual drift — CUSUM is designed for abrupt level changes; slow mean shifts accumulate in the statistic but detection delay grows proportionally.
- The target_mean and sigma parameters must be set correctly — if the reference mean is wrong, the CUSUM statistic drifts continuously and fires false alarms.
- One-directional variants miss shifts in the opposite direction; use two-sided CUSUM (default) for bidirectional monitoring.
- Does not separate seasonal effects from mean shifts — apply STL decomposition first on seasonal series.
- Minimum recommended sample: 20 observations in the reference window to estimate mean and std.
- FPR at defaults on stable data: ~0.5–2% depending on k (slack parameter).
- FPR at defaults on heavy-tailed data: 3–8%.

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Normal | (default) | (default) | STAT_SCALES defaults |
| Heavy-tailed (revenue, latency) | 6.0 | 10.0 | Raise threshold (h) to reduce false alarms |
| Seasonal series | N/A | N/A | Deseasonalise first (use STL + CUSUM) |
