# `outliers_multi.ecod`

> *Outlier fraction (ECOD)* — scores each row by the joint tail probability of its feature values using empirical CDFs, then reports the fraction of current rows above the reference 99th-percentile score.

## What it does

At fit time the detector stores the reference feature matrix. For each column `j` and each row `x`, the empirical CDF value `F̂ⱼ(xⱼ)` is computed against the reference column. The ECOD score for a row is `Σⱼ −log(min(F̂ⱼ(xⱼ), 1 − F̂ⱼ(xⱼ)))` — this accumulates high values for points in either tail of any feature. The 99th-percentile score over the reference is stored as the threshold. At score time current rows are scored against the reference ECDF and the fraction above the threshold is returned. ECOD requires no distributional assumptions and no kernel bandwidth selection.

## When to use it

- The default recommended multivariate outlier detector for high-dimensional tabular data — it scales linearly in both rows and features.
- When you want an assumption-free, parameter-light method: no bandwidth (`hbos`), no neighbour count (`lof`), no `ν` (`one_class_svm`).
- Detecting fraudulent bookings or transactions where extreme values across multiple numeric features simultaneously indicate anomaly.
- Tables with many numeric columns where HBOS's feature-independence assumption is acceptable but you want a more principled tail-probability aggregation.

## When not to use it

- When correlational outliers (normal marginals but unusual combination) are the primary target — ECOD scores each dimension independently like HBOS; use `mahalanobis_distance` or `lof` for those.
- When the reference is very small (< 200 rows) — ECDF estimates are noisy and score_threshold is unstable.
- Real-time single-row scoring is possible but requires keeping the full reference array in memory; for very large references consider down-sampling before fitting.

## Parameters

ECOD has no constructor parameters — it is fit-and-score only with a fixed 99th-percentile threshold.

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | — |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.05` |
| `fail_threshold` | `0.10` |
| `direction` | `lower_is_better` |
| `score meaning` | Fraction of rows with ECOD score above the reference 99th-percentile threshold; warn ≥ 5 %, fail ≥ 10 % |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.outliers_multi.ecod import ECODDetector

rng = np.random.default_rng(42)
n = 3000

# Gigler booking features: normal bookings
ref = pd.DataFrame({
    "amount_paid_usd":    rng.lognormal(mean=3.5, sigma=0.5, size=n),
    "session_duration_s": rng.normal(loc=180.0, scale=60.0, size=n).clip(10),
})

# Inject anomalies: high payment + extremely short session = possible bot fraud
fraudulent = pd.DataFrame({
    "amount_paid_usd":    rng.uniform(500, 1500, size=30),
    "session_duration_s": rng.uniform(1, 5, size=30),
})
curr = pd.concat([ref.sample(500, random_state=5), fraudulent], ignore_index=True)

det = ECODDetector()  # no tunable params; non-parametric empirical CDF method;
                      # the recommended default for high-dimensional tabular data
state = det.fit(ref)
result = det.score(curr, state)

print(result.verdict)        # fail
print(result.plain_english)  # "5.6% of rows with ECOD score above reference 99th percentile"
print(result.details)        # {"outlier_fraction": 0.056, "score_threshold": ...}
```

## Learn more

<!-- TODO: no simple YouTube explanation found -->

## Implementation

[`packages/dqt/src/dqt/algorithms/outliers_multi/ecod.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/outliers_multi/ecod.py)

## Reference

- Li, Z., Zhao, Y., Botta, N., Ionescu, C., & Hu, X. (2022). ECOD: Unsupervised Outlier Detection Using Empirical CDF Functions. *IEEE Transactions on Knowledge and Data Engineering*, 35(12), 12181–12193.
- `packages/dqt/src/dqt/algorithms/outliers_multi/ecod.py`

## Tests

`packages/dqt/tests/algorithms/outliers_multi/test_ecod.py`

## When it works well

- High-dimensional tabular datasets (many numeric columns) — ECOD uses empirical CDFs and requires no distributional assumptions.
- Excellent default for wide tables with heterogeneous column types; computationally efficient (O(n·d)).

## When it fails / Limitations

- Assumes feature independence — correlated features can cause over- or under-flagging; the score is a sum of tail probabilities across columns.
- Very small samples (< 50 rows) produce unstable empirical CDFs at the tails.
- Not suitable for purely categorical features.
- The contamination parameter controls the score threshold; setting it too low misses anomalies, too high increases FPR.
- Minimum recommended sample: 50 rows.
- FPR at defaults (contamination=0.1) on clean data: ~10%.
- FPR at defaults on heavy-tailed data: ~10–15%.

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Normal | (default) | (default) | STAT_SCALES defaults |
| Heavy-tailed (revenue, latency) | (default) | (default) | ECOD is distribution-agnostic |
| Sparse / high-null | N/A | N/A | Impute nulls before use |

## Failure modes and known limits

| Failure mode | Symptom | Fix |
|---|---|---|
| Skewed marginal distributions | ECOD uses empirical CDFs which are asymmetric for skewed data | Best for heavy-tailed data; use with log-transforms for revenue/latency columns |
| Requires N > 50 per feature | Empirical CDF estimates are noisy for small N | Increase baseline window |
| Default for high-dimensional tabular data | ECOD is dqt's default multivariate detector above 10 features | Override via `detector_slug` in checks.yaml if a different detector is preferred |
