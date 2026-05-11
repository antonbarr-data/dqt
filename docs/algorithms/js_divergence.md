# `drift.js_divergence`

> *Jensen-Shannon distance* — a symmetric, bounded measure of distributional difference derived from the square root of the JS divergence; score ∈ [0, 1] where 0 = identical distributions.

## What it does

At fit time, bins the reference column into `n_bins` equal-width buckets with additive smoothing (ε = 1e-8). At score time it bins the current window using the same edges and calls `scipy.spatial.distance.jensenshannon`, which returns the square root of the Jensen-Shannon divergence (i.e. the JS *distance*, not the divergence). The result is bounded in [0, 1]: 0 when the distributions are identical, 1 when they have disjoint supports. Unlike `kl_divergence`, the JS distance is symmetric — KL(cur ‖ ref) and KL(ref ‖ cur) are averaged through the mixture — making it a true metric.

## When to use it

- When you want a bounded, interpretable drift score that can be compared across columns of different types.
- As the primary drift metric for dashboard overviews where scores need to be on a common scale.
- When distributions can develop new modes in *either* window (JS is symmetric; KL is not).
- Good complement to `ks_pvalue`: KS gives a p-value, JS gives a normalised magnitude.

## When not to use it

- Categorical columns — use `chi_square_drift` or `cramers_v`.
- When you specifically need the asymmetric "cost of approximating current with reference" — use `kl_divergence`.
- Very small samples — sparse bins can dominate the score even with smoothing; prefer `wasserstein_1` on small windows.
- When a p-value is required — JS has no standard null distribution.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `n_bins` | `int` | `10` | Number of equal-width bins used to discretise the distribution |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.10` |
| `fail_threshold` | `0.20` |
| `direction` | `lower_is_better` |
| `score meaning` | JS distance ∈ [0, 1]; 0 = identical, 1 = maximally different (disjoint supports) |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.drift.divergence import JSDivergenceDetector

rng = np.random.default_rng(42)
# fct_bookings.amount_paid_usd — symmetric drift score for booking amount distributions
ref = pd.DataFrame({"amount_paid_usd": rng.normal(80, 20, 2000)})
curr_drift = pd.DataFrame({"amount_paid_usd": rng.normal(100, 20, 2000)})  # 1σ mean shift

det = JSDivergenceDetector(n_bins=10)
state = det.fit(ref)
result = det.score(curr_drift, state)
print(result.verdict)        # warn or fail
print(result.plain_english)  # "JS distance = 0.1742 — drift detected"
print(result.score)          # ~0.17

# stable window
curr_stable = pd.DataFrame({"amount_paid_usd": rng.normal(80, 20, 2000)})
result_stable = det.score(curr_stable, state)
print(result_stable.verdict)  # pass
print(result_stable.score)    # near 0
```

## Learn more

- 📺 [Jensen–Shannon (JS) Divergence for Machine Learning | Relation with KL Divergence | Explained](https://www.youtube.com/watch?v=0wtJNYaTB-8) — derives JS divergence from KL, proves it is symmetric and bounded in [0, 1], and shows practical examples comparing distributions.

## Reference

- Lin, J. (1991). Divergence measures based on the Shannon entropy. *IEEE Transactions on Information Theory*, 37(1), 145–151.
- `packages/dqt/src/dqt/algorithms/drift/divergence.py`

## Tests

`packages/dqt/tests/algorithms/drift/test_js_divergence.py`
