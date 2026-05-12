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

det = BOCPDDetector(
    hazard_lambda=250.0,  # expected run length between change points in time steps; 250 means
                          # "expect a change roughly every 250 observations"; lower to 50–100 for
                          # series where structural breaks are frequent; raise to 500+ for stable
                          # series to avoid spurious change points
)
state = det.fit(ref)
result = det.score(curr, state)

print(result.verdict)       # fail — high-confidence changepoint detected
print(result.score)         # > 0.80
print(result.plain_english) # "BOCPD max changepoint probability = 0.9312 (changepoint likely)"
print(result.details["max_changepoint_prob"])  # 0.93...
```

## Learn more

- 📺 [Bayesian Online Change-Point Detection — Schroders Tech Sessions](https://www.youtube.com/watch?v=cas__TaFk9U) — applied walkthrough of the Adams & MacKay algorithm in a production finance context, covering run-length posteriors and hazard priors.

## Implementation

[`packages/dqt/src/dqt/algorithms/timeseries/bocpd.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/timeseries/bocpd.py)

## Reference

- Adams, R. P., & MacKay, D. J. C. (2007). Bayesian online changepoint detection. *arXiv:0710.3742*.

## Tests

`packages/dqt/tests/algorithms/timeseries/test_bocpd.py`

## Score interpretation

Score = `max P(r≤1)` over the current window, where r is the run length (steps since last changepoint). Used instead of `P(r=0)` alone because `P(r=0)` is bounded at ~0.40 by competition with the grow-from-prior hypothesis under the hazard prior.

| Score | Interpretation |
|---|---|
| < 0.20 | Stable |
| 0.20–0.50 | Weak signal |
| ≥ 0.50 (warn) | Changepoint likely |
| ≥ 0.80 (fail) | Strong changepoint |

## Failure modes and known limits

| Failure mode | Symptom | Fix |
|---|---|---|
| Short reference window (< 50 rows) | max_run capped too low; long-run hypothesis not established | Use N ≥ 100 for reference |
| kappa0 too tight | Post-change observation equally unlikely under new and old prior; score stays near hazard | Default kappa0=0.1 is intentionally wide; do not increase it |
| hazard_lambda too small (< 10) | Prior CP probability > 0.10 per step; BOCPD fires constantly on noise | Default hazard_lambda=50 (2% prior per step) |
| Variance-only change | Mean-preserving scale shift does not move the score | Combine with `stl_residual_zscore` for variance-sensitive detection |
| Smooth gradual drift | Score stays low; no run-length hypothesis spikes | Use `adwin` or `page_hinkley` for gradual trends |

## When it works well

- Time series where you need probabilistic confidence in changepoint locations with uncertainty quantification.
- Works well for abrupt mean shifts in any numeric series; provides posterior run-length probabilities, not just a binary detection.

## When it fails / Limitations

- The failure modes already documented above (short reference window, kappa0, hazard_lambda, variance-only changes, gradual drift) cover the primary limitations.
- Variance-only changes (mean-preserving scale shifts) do not move the Gaussian conjugate score; combine with `stl_residual_zscore` for complete coverage.
- Minimum recommended sample: 100 observations for reliable posterior run-length estimates.
- FPR at defaults (hazard_lambda=50) on stable data: ~2% (1/hazard_lambda prior per step).
- FPR at defaults on heavy-tailed data: ~5–15%.

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Normal with abrupt shifts | (default) | (default) | STAT_SCALES defaults |
| Heavy-tailed (revenue, latency) | 0.20 | 0.50 | Raise score threshold |
| Gradual drift | N/A | N/A | Use adwin or page_hinkley instead |
