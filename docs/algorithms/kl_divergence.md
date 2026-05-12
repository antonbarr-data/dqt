# `drift.kl_divergence`

> *KL divergence* — measures the information loss when the reference distribution is used to approximate the current distribution; score = KL(current ‖ reference) over equal-width bins.

## What it does

At fit time, bins the reference column into `n_bins` equal-width buckets and stores the resulting probability distribution with additive smoothing (ε = 1e-8). At score time it bins the current window using the same edges, applies the same smoothing, and computes KL(cur ‖ ref) = Σ cur_p × ln(cur_p / ref_p). The result is non-negative (by Gibbs' inequality) and equals zero when both distributions are identical. Because KL is asymmetric — it penalises current mass where the reference has little — it is sensitive to new modes that were absent in the reference.

## When to use it

- When you want to quantify how many nats of information current samples "cost" relative to the reference model.
- In complement with `js_divergence` when asymmetry is desirable: KL(cur ‖ ref) is high if the current distribution has mass in regions the reference did not cover.
- Pipeline-level drift summaries where additive scores across multiple columns are aggregated.
- When the distribution change involves new modes appearing in the current window.

## When not to use it

- Categorical columns — use `chi_square_drift` or `cramers_v`.
- When you need a bounded, symmetric score — use `js_divergence` (bounded [0, 1]) instead.
- Very small samples where bins have zero counts — smoothing mitigates this but can inflate the score for sparse windows.
- When a p-value is required — KL has no closed-form null distribution; use `ks_pvalue` for hypothesis testing.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `n_bins` | `int` | `10` | Number of equal-width bins used to discretise the distribution |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.10` |
| `fail_threshold` | `0.30` |
| `direction` | `lower_is_better` |
| `score meaning` | KL divergence in nats; 0 = identical distributions; unbounded above |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.drift.divergence import KLDivergenceDetector

rng = np.random.default_rng(42)
# fct_bookings.amount_paid_usd — detect a new high-value tier emerging in booking amounts
ref = pd.DataFrame({"amount_paid_usd": rng.normal(80, 20, 2000)})
# current: shifted mean + a new high-value mode (premium package launched)
curr_shifted = pd.DataFrame({"amount_paid_usd": np.concatenate([
    rng.normal(85, 20, 1900),
    rng.normal(500, 10, 100),   # new premium tier
])})

det = KLDivergenceDetector(
    n_bins=10,  # bins for histogram approximation; 10 is a reasonable default;
                # KL is asymmetric (measures cost of approximating current with reference),
                # so interpret directionally; increase to 20+ for smoother distributions
)
state = det.fit(ref)
result = det.score(curr_shifted, state)
print(result.verdict)        # warn or fail
print(result.plain_english)  # "KL divergence = 0.1823 — drift detected"
print(result.score)          # ~0.18
```

## Learn more

- 📺 [Intuitively Understanding the KL Divergence](https://www.youtube.com/watch?v=SxGYPqCgJWM) — builds geometric intuition for KL divergence, explains its asymmetry, and contrasts it with symmetric alternatives like JS divergence.

## Implementation

[`packages/dqt/src/dqt/algorithms/drift/divergence.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/drift/divergence.py)

## Reference

- Kullback, S., & Leibler, R. A. (1951). On information and sufficiency. *Annals of Mathematical Statistics*, 22(1), 79–86.
- `packages/dqt/src/dqt/algorithms/drift/divergence.py`

## Tests

`packages/dqt/tests/algorithms/drift/test_kl_divergence.py`

## When it works well

- Continuous numeric columns with well-overlapping support in reference and current distributions.
- Useful as an information-theoretic drift measure when you need sensitivity to tail changes and shape differences.

## When it fails / Limitations

- Zero-probability reference bins cause infinite KL divergence — requires Laplace smoothing (applied automatically), but this inflates the score for sparse distributions.
- Asymmetric — KL(P||Q) ≠ KL(Q||P); the score depends on the direction of comparison. Use `js_divergence` for a symmetric alternative.
- Heavily sensitive to bin count choice — more bins increase sensitivity but also noise; the implementation uses Sturges' rule by default.
- Categorical columns with many unique values produce sparse bins and unreliable estimates.
- Minimum recommended sample: 100 rows (both reference and current).
- FPR at defaults on stable normal data: ~5–10%.
- FPR at defaults on heavy-tailed data: ~10–20%.

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Normal | (default) | (default) | STAT_SCALES defaults |
| Heavy-tailed (revenue, latency) | 0.20 | 0.50 | Wider bands; heavy tails inflate KL |
| Sparse / high-null | N/A | N/A | Use null_fraction first |
