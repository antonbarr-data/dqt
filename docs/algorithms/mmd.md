# `drift.mmd`

> *MMD drift* — measures the distance between two multivariate distributions using the Maximum Mean Discrepancy statistic with an RBF kernel; score = clipped MMD² in [0, 1].

## What it does

At fit time the detector sub-samples up to 500 rows from the reference DataFrame and estimates the RBF kernel bandwidth `γ` via the median heuristic (`γ = 1 / (2 × median²(pairwise distances))`). At score time it sub-samples up to 500 rows from the current window and computes the biased MMD² estimator:

```
MMD²(X, Y) = E[k(x,x')] + E[k(y,y')] − 2·E[k(x,y)]
```

where `k(a,b) = exp(−γ ‖a−b‖²)`. A value near 0 means the two samples are drawn from the same distribution; larger values signal drift. The score is clipped to [0, 1].

## When to use it

- Multivariate drift detection when you care about the full joint distribution shift, not just marginal column-by-column changes.
- Continuous numeric columns at any dimensionality — the RBF kernel handles non-linear structure that PSI or KL divergence (which bin each column independently) would miss.
- When you want a single scalar drift signal across an entire feature set rather than per-column p-values.
- Complements `ks_pvalue` for univariate checks: run MMD at the table level, KS at the column level.

## When not to use it

- Very large datasets without sub-sampling — kernel matrix computation is O(n²); the built-in cap at 500 rows per side trades some statistical power for tractability.
- Categorical columns — convert them to numeric (ordinal or one-hot) before feeding; MMD ignores non-numeric columns.
- When you need a calibrated p-value — the biased MMD² estimator does not come with an analytic null distribution at this implementation level; use as a score-based signal, not a formal test.
- Univariate drift where `ks_pvalue` or `wasserstein_1` gives more interpretable results.

## Parameters

MMD has no constructor parameters — bandwidth is estimated automatically from each reference batch via the median heuristic.

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | — |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.10` |
| `fail_threshold` | `0.20` |
| `direction` | `lower_is_better` |
| `score meaning` | MMD²; 0 = identical distributions, 1 = maximally different; warn ≥ 0.10, fail ≥ 0.20 |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.drift.mmd import MMDDetector

rng = np.random.default_rng(42)
n = 2000

# Gigler gig prices — reference window (last 30 days, stable market)
ref = pd.DataFrame({
    "price_usd": rng.lognormal(mean=3.5, sigma=0.5, size=n),
})

# Current window after a competitor exits — prices shift up
curr_drift  = pd.DataFrame({"price_usd": rng.lognormal(mean=4.2, sigma=0.5, size=n)})
# Current window with no real change
curr_stable = pd.DataFrame({"price_usd": rng.lognormal(mean=3.5, sigma=0.5, size=n)})

det = MMDDetector()
state = det.fit(ref)

result_drift = det.score(curr_drift, state)
print(result_drift.verdict)        # fail
print(result_drift.plain_english)  # "MMD² = 0.2341 — drift detected"
print(result_drift.score)          # ~0.23

result_stable = det.score(curr_stable, state)
print(result_stable.verdict)       # pass
print(result_stable.score)         # near 0.0
```

## Learn more

- 📺 [Maximum Mean Discrepancy: How to Compare High-Dimensional Data](https://www.youtube.com/watch?v=KuzEm1VhJYE) — explains MMD as a statistical framework for determining whether two datasets come from different distributions, with intuitive kernel diagrams.

## Reference

- Gretton, A., Borgwardt, K.M., Rasch, M.J., Schölkopf, B., & Smola, A. (2012). A Kernel Two-Sample Test. *Journal of Machine Learning Research*, 13, 723–773.
- `packages/dqt/src/dqt/algorithms/drift/mmd.py`

## Tests

`packages/dqt/tests/algorithms/drift/test_mmd.py`
