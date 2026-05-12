# `outliers_multi.mahalanobis_distance`

> *Outlier fraction (Mahal.)* — flags multivariate outliers by measuring how many rows fall outside the chi-square critical ellipsoid defined by the reference covariance structure.

## What it does

At fit time the detector records the column-wise mean vector and inverse covariance matrix of all numeric columns in the reference DataFrame. At score time it computes the squared Mahalanobis distance `d²(x) = (x − μ)ᵀ Σ⁻¹ (x − μ)` for every row in the current window, then counts the fraction where `d²` exceeds the chi-square critical value at `df = n_features` and `p = p_threshold`. Rows beyond that threshold are considered multivariate outliers. The covariance inverse is regularised by adding `ε·I` to avoid singularity; if that still fails, `np.linalg.pinv` is used.

## When to use it

- Datasets with moderate dimensionality (2–20 numeric columns) where correlations between columns are stable and meaningful.
- Detecting sellers or buyers whose joint profile (e.g. review count + price + response time) deviates from the typical distribution while each dimension individually looks fine.
- When the reference population is approximately multivariate normal — the chi-square threshold is exact under normality.
- Good complement to univariate detectors: catches only the cases that correlations expose.

## When not to use it

- High-dimensional data (> 50 columns) — the covariance estimate degenerates and the chi-square approximation breaks down; use `ecod` or `isolation_forest_fraction` instead.
- Very small reference samples (< 5 × n_features rows) — covariance estimation is unreliable.
- Heavy-tailed or strongly non-normal distributions — the chi-square threshold over-flags tails; use robust MCD-based Mahalanobis or `lof` for those.
- Categorical columns — the detector silently ignores non-numeric columns; make sure all informative columns are numeric.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `p_threshold` | `float` | `0.001` | Chi-square tail probability used as the outlier boundary. Rows where `d² > chi2.ppf(1 − p_threshold, df)` are flagged. Lower values flag fewer rows. |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.01` |
| `fail_threshold` | `0.05` |
| `direction` | `lower_is_better` |
| `score meaning` | Fraction of rows outside the chi-square critical ellipsoid at `p = p_threshold`; warn ≥ 1 %, fail ≥ 5 % |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.outliers_multi.mahalanobis import MahalanobisDetector

rng = np.random.default_rng(42)
n = 2000

# Typical Gigler seller profiles: reviews/month, avg price, response time
ref = pd.DataFrame({
    "num_reviews_per_month": rng.normal(8.0, 2.5, n),
    "avg_price_usd":         rng.normal(45.0, 15.0, n),
    "response_time_h":       rng.normal(3.0, 1.0, n),
})

# Inject suspicious sellers: very high reviews + unusually low prices + near-zero response
suspicious = pd.DataFrame({
    "num_reviews_per_month": rng.normal(80.0, 5.0, 50),   # outlier
    "avg_price_usd":         rng.normal(2.0, 0.5, 50),    # outlier
    "response_time_h":       rng.normal(0.1, 0.05, 50),   # outlier
})
curr = pd.concat([ref.sample(500, random_state=1), suspicious], ignore_index=True)

det = MahalanobisDetector(
    p_threshold=0.001,  # chi-square tail probability; 0.001 flags the most extreme 0.1% of rows;
                        # raise to 0.01 for more sensitive alerting;
                        # only valid when columns are approximately multivariate normal
)
state = det.fit(ref)
result = det.score(curr, state)

print(result.verdict)        # fail — outlier fraction well above 5 %
print(result.plain_english)  # "8.9% of rows outside Mahalanobis chi-square ellipsoid (p=0.001)"
print(result.details)        # {"outlier_fraction": 0.089, "chi2_threshold": ..., "n_rows": 550}
```

## Learn more

- 📺 [Mahalanobis Distance — intuitive understanding through graphs and tables](https://www.youtube.com/watch?v=3IdvoI8O9hU) — builds from Euclidean distance to the full multi-dimensional ellipsoid with clear visual examples.

## Implementation

[`packages/dqt/src/dqt/algorithms/outliers_multi/mahalanobis.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/outliers_multi/mahalanobis.py)

## Reference

- Mahalanobis, P.C. (1936). On the generalised distance in statistics. *Proceedings of the National Institute of Sciences of India*, 2(1), 49–55.
- `packages/dqt/src/dqt/algorithms/outliers_multi/mahalanobis.py`

## Tests

`packages/dqt/tests/algorithms/outliers_multi/test_mahalanobis_distance.py`

## When it works well

- Multivariate numeric datasets with correlated Gaussian-like features — accounts for covariance structure that univariate detectors miss.
- Works well when anomalies are unusual combinations of individually normal values (e.g. revenue high + quantity low simultaneously).

## When it fails / Limitations

- Non-Gaussian marginals or non-linear dependencies — the covariance matrix captures only linear relationships; use `isolation_forest_fraction` or `lof` instead.
- Singular or near-singular covariance matrix (highly correlated or duplicate columns) — inversion fails; use MCD (Minimum Covariance Determinant) variant or reduce dimensionality first.
- More columns than rows (p > n) — the sample covariance matrix is not full rank; use `isolation_forest_fraction` instead.
- Minimum recommended sample: max(100, 5 × number_of_columns) rows.
- FPR at defaults on clean multivariate-normal data: ~1% (chi-squared threshold at 99th percentile).
- FPR at defaults on heavy-tailed data: 5–20% depending on tail heaviness.

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Normal (multivariate) | (default) | (default) | STAT_SCALES defaults |
| Heavy-tailed (revenue, latency) | N/A | N/A | Use isolation_forest_fraction instead |
| Sparse / high-null | N/A | N/A | Impute nulls before use |

## Failure modes and known limits

| Failure mode | Symptom | Fix |
|---|---|---|
| Singular covariance matrix | When features are collinear, standard covariance is singular; `pinv` fallback used automatically | A warning is logged when `pinv` is used; consider PCA whitening to remove collinearity |
| N < p (fewer samples than features) | Covariance estimate is rank-deficient; MCD is less reliable | Use LOF or ECOD for high-dimensional data with small N |
| Non-Gaussian features | Mahalanobis p-values assume chi-square distribution of distances; skewed features inflate FPR | Transform skewed features (log, box-cox) before use |

## Recommended use

Best for: correlated numeric features, moderate N>>p. The p_threshold parameter maps directly to chi-square critical value (e.g. p_threshold=0.001 means chi-square critical at 0.1%).
