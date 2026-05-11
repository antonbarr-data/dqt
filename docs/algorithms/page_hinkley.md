# `timeseries.page_hinkley`

> *Page-Hinkley alarm* — online sequential test that signals a permanent upward mean shift by accumulating signed deviations and alarming when the running total drifts far above its historical minimum.

## What it does

At fit time, computes the reference mean (μ) and standard deviation (σ), then scales the two hyperparameters by σ so the detector is unit-free. At score time it runs the Page-Hinkley recurrence: PH_t = Σ(x_i − μ − δ), where δ is a small tolerance that prevents drift due to noise. An alarm fires when PH_t − min(PH) > λ, meaning the cumulative sum has climbed far above its own running minimum. The reported score is (PH − min_PH) / λ, normalised so score = 1.0 is exactly at the alarm boundary. Because δ and λ are scaled by the reference σ, the same nominal parameter values work across metrics with different units and magnitudes.

## When to use it

- Detecting a one-directional (upward) mean shift in a streaming metric, e.g. average gig price creeping upward after a platform policy change.
- Online/incremental pipelines where you cannot buffer the full window — the recurrence is O(1) per new observation.
- When the exact change-point time matters: PH_t − min_PH identifies approximately when the shift began.
- Complement to CUSUM: CUSUM is two-sided (both up and down shifts); Page-Hinkley as implemented here detects upward shifts — run two instances for bidirectional monitoring.

## When not to use it

- Bidirectional shifts in one pass — use CUSUM (two-sided) instead.
- Abrupt spike-and-recover anomalies — PH accumulates slowly and is not designed for transient outliers; use `stl_residual_zscore` or `generalized_esd`.
- Non-stationary reference (strong trend) — detrend first; an upward trend will continuously accumulate PH even with no change-point.
- Heavy-tailed distributions where extreme values dominate the cumulative sum; consider truncating or winsorising the input.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `delta` | `float` | `0.005` | Tolerance in units of reference σ; absorbs small random fluctuations. Increase for noisy series with high σ relative to the shift you care about. |
| `lambda_` | `float` | `100.0` | Alarm threshold in units of reference σ × n; higher values reduce false-alarm rate at the cost of slower detection. Scaled by σ at fit time. |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.5` |
| `fail_threshold` | `1.0` |
| `direction` | `lower_is_better` |
| `score meaning` | Normalised PH statistic (PH − min_PH) / λ; warn at 0.5 (approaching alarm boundary), fail at ≥ 1.0 (alarm triggered) |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.timeseries.page_hinkley import PageHinkleyDetector

rng = np.random.default_rng(0)
dates = pd.date_range("2024-01-01", periods=120, freq="D")

# fct_gigs: average daily price_usd — stable then a pricing strategy shift
baseline_prices = rng.normal(loc=85.0, scale=8.0, size=90)
elevated_prices = rng.normal(loc=102.0, scale=8.0, size=30)   # ~20% price increase

ref = pd.DataFrame({"avg_price_usd": baseline_prices}, index=dates[:90])
curr = pd.DataFrame({"avg_price_usd": elevated_prices}, index=dates[90:])

det = PageHinkleyDetector(delta=0.005, lambda_=100.0)
state = det.fit(ref)
result = det.score(curr, state)

print(result.verdict)        # fail — upward mean shift detected
print(result.score)          # > 1.0
print(result.plain_english)  # "Page-Hinkley statistic = ... → score=1.23 (alarm)"
print(result.details["ph_statistic"])   # accumulated PH value
print(result.details["ref_mean"])       # ~85.0
```

## Learn more

- 📺 [Change Point Detection Algorithms — The Alan Turing Institute](https://www.youtube.com/watch?v=yidQ5G-jKf0) — overview of online and offline change-point methods including cumulative-sum families; contextualises Page-Hinkley among competing approaches.

## Reference

- Hinkley, D. V. (1971). Inference about the change-point from cumulative sum tests. *Biometrika*, 58(3), 509–523.
- `packages/dqt/src/dqt/algorithms/timeseries/page_hinkley.py`

## Tests

`packages/dqt/tests/algorithms/timeseries/test_page_hinkley.py`
