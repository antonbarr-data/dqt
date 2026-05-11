# `timeseries.bocpd`

> *Changepoint probability* — maintains a Bayesian posterior over run lengths to compute the real-time probability of a changepoint at each new observation, without requiring the number of changepoints to be specified in advance.

## What it does

At fit time, estimates the prior hyperparameters (μ₀, κ₀, α₀, β₀) of a Normal-Inverse-χ² conjugate from the reference window, and stores the raw reference values for use at score time. At score time, the reference and current series are concatenated and fed to the truncated BOCPD recurrence. For each time step the algorithm maintains a set of run-length hypotheses — one for each possible time since the last changepoint — weighted by their posterior probability. A Gaussian observation likelihood (with Student-t predictive distribution for robustness) updates the weights at each step. The hazard rate 1/λ encodes the prior belief about changepoint frequency. The reported score is the maximum posterior changepoint probability over the current portion of the window; score ≥ 0.5 means the algorithm considers a changepoint more likely than not. The run-length hypothesis set is truncated at `max_run = len(reference) // 2` to prevent unbounded memory growth.

## When to use it

- Detecting strategy-level shifts in a metric — e.g. a step-change in `fct_gigs.price_usd` after a pricing policy change.
- When you need probabilistic estimates rather than binary alarms — the posterior gives a confidence level for each candidate changepoint.
- Series where the number and timing of changepoints is unknown in advance.
- Online monitoring: the recurrence processes each new observation in O(t) time (capped at O(max_run) with truncation).

## When not to use it

- Short-lived spikes — BOCPD detects persistent regime changes, not momentary anomalies; use `stl_residual_zscore` for spikes.
- Gradual (ramp) shifts — the Gaussian likelihood model responds most strongly to abrupt level changes; CUSUM is better suited for slow drifts.
- Very long series without truncation tuning — `max_run` defaults to half the reference length; if the reference is short, consider setting `hazard_lambda` to match the expected regime duration.
- Multivariate changepoints — this implementation is univariate; extend with a multivariate likelihood if needed.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `hazard_lambda` | `float` | `250.0` | Expected run length between changepoints (in observations). A value of 250 means the prior expects a changepoint roughly every 250 steps. Smaller values increase sensitivity to short regimes. |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.50` |
| `fail_threshold` | `0.80` |
| `direction` | `lower_is_better` |
| `score meaning` | Maximum posterior probability of a changepoint in the current window; warn at ≥ 0.50 (more likely than not), fail at ≥ 0.80 (high confidence changepoint) |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.timeseries.bocpd import BOCPDDetector

rng = np.random.default_rng(99)
dates = pd.date_range("2024-01-01", periods=120, freq="D")

# fct_gigs.price_usd daily median — pricing strategy shift mid-monitoring
regime_a = rng.normal(loc=75.0, scale=6.0, size=90)   # baseline pricing
regime_b = rng.normal(loc=95.0, scale=6.0, size=30)   # new premium tier strategy

ref = pd.DataFrame({"median_price_usd": regime_a}, index=dates[:90])
curr = pd.DataFrame({"median_price_usd": regime_b}, index=dates[90:])

det = BOCPDDetector(hazard_lambda=250.0)
state = det.fit(ref)
result = det.score(curr, state)

print(result.verdict)       # fail — high-confidence changepoint detected
print(result.score)         # > 0.80
print(result.plain_english) # "BOCPD max changepoint probability = 0.9312 (changepoint likely)"
print(result.details["max_changepoint_prob"])  # 0.93...
```

## Learn more

- 📺 [Bayesian Online Change-Point Detection — Schroders Tech Sessions](https://www.youtube.com/watch?v=cas__TaFk9U) — applied walkthrough of the Adams & MacKay algorithm in a production finance context, covering run-length posteriors and hazard priors.

## Reference

- Adams, R. P., & MacKay, D. J. C. (2007). Bayesian online changepoint detection. *arXiv:0710.3742*.
- `packages/dqt/src/dqt/algorithms/timeseries/bocpd.py`

## Tests

`packages/dqt/tests/algorithms/timeseries/test_bocpd.py`
