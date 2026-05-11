# `drift.ks_pvalue`

> *KS drift (1−p)* — detects distribution drift between a reference and current window using the two-sample Kolmogorov-Smirnov test; score = 1 − p-value.

## What it does

Stores the reference column values at fit time. At score time it runs `scipy.stats.ks_2samp` between the reference array and the current window, producing a KS statistic (maximum absolute difference between the two empirical CDFs) and a p-value. The reported score is `1 − p-value` so that higher scores indicate more evidence of drift. A score above 0.95 (p < 0.05) triggers a warning; above 0.99 (p < 0.01) triggers a failure. The detector uses the first column of the input DataFrame.

## When to use it

- Continuous numeric columns where you want a non-parametric, distribution-free drift test.
- When sample sizes are moderate to large (≥ 100 per window) — KS power grows with n.
- As the canonical drift test on any numeric column where you have no prior on the distribution shape.
- Good default for automated baselining pipelines because it requires no parameter tuning.

## When not to use it

- Categorical columns — use `chi_square_drift` or `cramers_v` instead.
- Very small samples (< 30) — power is low and p-values are unreliable.
- Heavy-tailed distributions where a small shift in the bulk matters more than tail behaviour; consider `wasserstein_1` or `psi` for magnitude-sensitive drift.
- When you need a drift *magnitude* rather than a hypothesis test score; the KS statistic measures the supremum of CDF difference, not the total area.

## Parameters

This detector has no constructor parameters — it is fit-and-score only.

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | — |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.95` |
| `fail_threshold` | `0.99` |
| `direction` | `lower_is_better` |
| `score meaning` | `1 − p-value` from two-sample KS test; warn at p < 0.05, fail at p < 0.01 |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.drift.ks2sample import KS2SampleDetector

rng = np.random.default_rng(42)
# fct_bookings.amount_paid_usd — detect booking amount drift between two weekly windows
ref = pd.DataFrame({"amount_paid_usd": rng.normal(80, 20, 1000)})
curr_drift = pd.DataFrame({"amount_paid_usd": rng.normal(100, 20, 1000)})  # mean shift (+$20)
curr_stable = pd.DataFrame({"amount_paid_usd": rng.normal(80, 20, 1000)})

det = KS2SampleDetector()
state = det.fit(ref)

result_drift = det.score(curr_drift, state)
print(result_drift.verdict)        # fail (large shift)
print(result_drift.plain_english)  # "KS test p=0.0000 — drift detected"
print(result_drift.score)          # ~1.0

result_stable = det.score(curr_stable, state)
print(result_stable.verdict)       # pass
print(result_stable.score)         # low value, e.g. 0.32
```

## Learn more

- 📺 [Kolmogorov-Smirnov Test Explained | Data Science Fundamentals](https://www.youtube.com/watch?v=VpQ6MLoRSfY) — explains the KS statistic as the maximum gap between two empirical CDFs and shows how the p-value is derived.

## Reference

- Kolmogorov, A. N. (1933). Sulla determinazione empirica di una legge di distribuzione. *Giornale dell'Istituto Italiano degli Attuari*, 4, 83–91.
- Smirnov, N. V. (1948). Table for estimating the goodness of fit of empirical distributions. *Annals of Mathematical Statistics*, 19(2), 279–281.
- `packages/dqt/src/dqt/algorithms/drift/ks2sample.py`

## Tests

`packages/dqt/tests/algorithms/drift/test_ks_pvalue.py`
