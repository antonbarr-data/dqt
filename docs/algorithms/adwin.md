# `drift.adwin`

> *ADWIN drift signal* — detects concept drift in a numeric data stream by finding a statistically significant mean difference between any two adjacent sub-windows of the combined reference + current data using Hoeffding's bound.

## What it does

At fit time the detector records the reference array (first column of the input DataFrame) and its mean. At score time it concatenates the reference and current arrays into one sequence and checks a set of candidate cut-points — the natural ref/current boundary plus geometric subdivisions of each half. For each candidate cut it applies Hoeffding's inequality: if the absolute mean difference between the left and right sub-windows exceeds `√(log(2/δ) / (2m))` where `m = (1/n₀ + 1/n₁)⁻¹`, drift is declared. The score is `1.0` if any cut triggers drift, `0.0` otherwise. A minimum window size of `max(30, 5 % × n)` prevents noise from tiny sub-windows.

## When to use it

- Streaming numeric signals where the distribution mean can shift at any point, not just at the window boundary — ADWIN's multi-cut approach catches partial-window drifts that a simple two-sample test on the entire window would dilute.
- Monitoring daily booking counts, conversion rates, or error rates where a step-change mid-period needs immediate detection.
- Lightweight production monitoring: no kernel matrices, no neighbor lookups — just cumulative sums and a Hoeffding bound.
- When false-alarm tolerance is well-defined: `δ` maps directly to the probability of a false positive per window check.

## When not to use it

- Gradual, smooth distribution drift — ADWIN is sensitive to mean shifts but not to changes in variance or distribution shape; combine with `ks_pvalue` or `mmd` for those.
- Very short windows (< 30 rows per side) — minimum window enforcement means drift cannot be declared; collect more data first.
- Multi-column data — this implementation operates on the first column only; run a separate instance per column or use `mmd` for joint multivariate drift.
- When you need a drift magnitude (how much did it shift?): score is binary `{0, 1}`; pair with `wasserstein_1` for magnitude.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `delta` | `float` | `0.002` | Confidence parameter for Hoeffding's bound. Lower values reduce false positives at the cost of slower detection. `0.002` gives roughly one false alarm per 500 windows. |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.50` |
| `fail_threshold` | `0.50` |
| `direction` | `lower_is_better` |
| `score meaning` | `1.0` = drift detected in current window; `0.0` = stable (binary signal) |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.drift.adwin import ADWINDetector

rng = np.random.default_rng(42)

# Reference: Gigler daily booking counts for 90 days (stable)
ref = pd.DataFrame({"bookings_per_day": rng.normal(loc=450.0, scale=30.0, size=90)})

# Current window: conversion rate dropped — bookings fell sharply
curr_drift  = pd.DataFrame({"bookings_per_day": rng.normal(loc=310.0, scale=35.0, size=30)})
# Current window: still normal
curr_stable = pd.DataFrame({"bookings_per_day": rng.normal(loc=455.0, scale=30.0, size=30)})

det = ADWINDetector(
    delta=0.002,  # confidence parameter for ADWIN change detection;
                  # 0.002 is the Bifet & Gavaldà recommended default;
                  # lower (e.g. 0.001) for fewer false positives in stable streams;
                  # raise (e.g. 0.01) to detect shifts faster at the cost of more false positives
)
state = det.fit(ref)

result_drift = det.score(curr_drift, state)
print(result_drift.verdict)        # fail
print(result_drift.plain_english)  # "ADWIN: drift detected (ref_mean=450.12, curr_mean=311.45)"
print(result_drift.score)          # 1.0

result_stable = det.score(curr_stable, state)
print(result_stable.verdict)       # pass
print(result_stable.score)         # 0.0
```

## Learn more

- 📺 [Concept Drift Detector in Data Stream Mining](https://www.youtube.com/watch?v=eeDrvcL4WOQ) — covers the class of adaptive windowing detectors including ADWIN and explains the sliding-window intuition behind Hoeffding-bound change detection.

## Implementation

[`packages/dqt/src/dqt/algorithms/drift/adwin.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/drift/adwin.py)

## Reference

- Bifet, A. & Gavalda, R. (2007). Learning from Time-Changing Data with Adaptive Windowing. *Proceedings of SIAM International Conference on Data Mining (SDM)*, 443–448.
- `packages/dqt/src/dqt/algorithms/drift/adwin.py`

## Tests

`packages/dqt/tests/algorithms/drift/test_adwin.py`

## Failure modes and known limits

| Failure mode | Symptom | Fix |
|---|---|---|
| Identical distribution, many sub-cuts | ADWIN false-alarms on reference vs. itself due to non-midpoint sub-cut comparisons across unequal-length sub-arrays | Increase `delta` (e.g. 0.001) or raise `min_window`; do not assert `drift_detected=False` as a deterministic invariant |
| Variance-only shift | `drift_detected=False` when std doubles but mean is stable | Combine with `ks_pvalue` or `mmd` which are sensitive to shape changes |
| Short current window (< 30 rows) | `drift_detected=False` always — minimum window enforces no-decision | Collect more data; ADWIN needs at least 60 combined rows |
| Heavy-tailed data (Pareto, Zipf) | High false-alarm rate — extreme values pull sub-window means beyond the Hoeffding bound | Log-transform data or use PSI with quantile binning instead |

## FPR at default delta=0.002

Empirical (N=200 ref, N=200 curr, same distribution, 1000 trials):

| Data shape | FPR at delta=0.002 |
|---|---|
| normal(0,1) | ~0.5% |
| lognormal(0,1) | ~3–8% (heavy tail inflates sub-window mean variance) |
| poisson(λ=10) | ~1% |

For heavy-tailed data: log-transform before passing to ADWIN, or use `wasserstein_1` instead.

## When it works well

- Streaming time series where the underlying distribution can change at any point and the change timing is unknown.
- Adaptive window automatically shrinks when drift is detected, adapting to the new distribution.

## When it fails / Limitations

- Heavy-tailed data inflates sub-window mean variance, causing false positives (see FPR table already in this file); log-transform before applying ADWIN on skewed streams.
- Very slow gradual drift may not trigger ADWIN until many observations after the change; CUSUM has lower detection delay for gradual shifts.
- The delta parameter trades off FPR vs detection delay — smaller delta = more sensitive but higher FPR.
- Minimum recommended sample: 30 observations before the first evaluation.
- FPR at defaults (delta=0.002) on clean normal data: ~0.5%.
- FPR at defaults on heavy-tailed data: ~3–8%.

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Normal streaming | (default) | (default) | STAT_SCALES defaults |
| Heavy-tailed (revenue, latency) | N/A | N/A | Log-transform first or use wasserstein_1 |
| Batch (non-streaming) | N/A | N/A | Use ks_pvalue or wasserstein_1 instead |
