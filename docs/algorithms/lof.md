# `outliers_multi.lof`

> *Outlier fraction (LOF)* — flags rows whose local density is significantly lower than the density of their neighbours, making them locally anomalous even when they would not be caught by a global threshold.

## What it does

At fit time the detector trains a scikit-learn `LocalOutlierFactor` model (novelty mode) on the numeric columns of the reference DataFrame and records the 99th percentile of the negative LOF scores as the threshold. At score time it scores each row in the current window using the fitted model. LOF for a point computes the ratio of the average local reachability density of its `n_neighbors` neighbours to its own local reachability density; values substantially greater than 1.0 indicate the point is in a sparser region than its neighbours. The score is the fraction of current rows exceeding the reference 99th-percentile threshold.

## When to use it

- Datasets with non-convex or irregular cluster shapes where distance-based detectors (Mahalanobis, Isolation Forest) miss intra-cluster outliers.
- Detecting anomalous gig listings where price and delivery time are jointly unusual for a specific sub-market (e.g. $200 logo designs delivered in 1 hour — normal globally, anomalous in context).
- When cluster density varies across the feature space — LOF adapts the density estimate locally.
- Moderate dimensionality (2–15 features) where nearest-neighbour distance is still meaningful.

## When not to use it

- Very high dimensions (> 30 features) — nearest-neighbour distances concentrate and LOF loses contrast; use `ecod` or `isolation_forest_fraction` instead.
- Large scoring batches (> 50 k rows) — `score_samples` is O(n × k) and can be slow; consider `hbos` for throughput-sensitive pipelines.
- Streaming / one-row-at-a-time scoring — the fitted `LocalOutlierFactor` requires a batch; use `adwin` for streams.
- When you need a calibrated probability of outlierness rather than a rank-based threshold; LOF scores are not probabilities.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `n_neighbors` | `int` | `20` | Number of neighbours used to estimate local density. Larger values smooth the density estimate; smaller values make it more sensitive to micro-clusters. Capped to `len(reference) − 1` automatically. |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.05` |
| `fail_threshold` | `0.10` |
| `direction` | `lower_is_better` |
| `score meaning` | Fraction of rows with LOF score above the reference 99th-percentile threshold; warn ≥ 5 %, fail ≥ 10 % |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.outliers_multi.lof import LOFDetector

rng = np.random.default_rng(42)
n = 2000

# Typical Gigler gig listings
ref = pd.DataFrame({
    "price_usd":      rng.lognormal(mean=3.5, sigma=0.6, size=n),  # log-normal price
    "delivery_days":  rng.integers(1, 30, size=n).astype(float),
})

# Inject anomalous combos: very cheap + very long, or very expensive + instant
anomalous = pd.DataFrame({
    "price_usd":     [5.0, 5.0, 5.0, 2000.0, 1800.0],
    "delivery_days": [28.0, 29.0, 30.0, 1.0, 1.0],
})
curr = pd.concat([ref.sample(500, random_state=7), anomalous], ignore_index=True)

det = LOFDetector(
    n_neighbors=20,  # neighbourhood size; 20 is a robust default;
                     # increase to 50 for large datasets (>100k rows) to get more stable density estimates;
                     # decrease to 10 for sparse datasets or when clusters are small
)
state = det.fit(ref)
result = det.score(curr, state)

print(result.verdict)        # warn or fail
print(result.plain_english)  # "1.0% of rows with LOF score above reference 95th percentile"
print(result.details["outlier_fraction"])  # fraction flagged
```

## Learn more

- 📺 [Local Outlier Factor (LOF) for Anomaly Detection — Unsupervised Machine Learning](https://www.youtube.com/watch?v=CiJ95in4KQc) — walks through local reachability density step by step with visual examples of why global thresholds miss density-based outliers.

## Implementation

[`packages/dqt/src/dqt/algorithms/outliers_multi/lof.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/outliers_multi/lof.py)

## Reference

- Breunig, M.M., Kriegel, H-P., Ng, R.T., & Sander, J. (2000). LOF: Identifying Density-Based Local Outliers. *ACM SIGMOD Record*, 29(2), 93–104.
- `packages/dqt/src/dqt/algorithms/outliers_multi/lof.py`

## Tests

`packages/dqt/tests/algorithms/outliers_multi/test_lof.py`

## When it works well

- Datasets with non-uniform density clusters — LOF detects local outliers that are far from their neighbours even when they would appear normal globally.
- Medium-dimensional feature sets (2–20 columns) where local neighbourhood structure is meaningful.

## When it fails / Limitations

- Clusters of very different densities — LOF's local reachability density comparison can misidentify dense-cluster members as outliers when adjacent to sparse clusters.
- Very high dimensions (> 20 columns) — the "curse of dimensionality" makes nearest-neighbour distances uninformative; use `isolation_forest_fraction` or `ecod` instead.
- Computationally O(n²) without approximation — slow for samples > 50,000 rows.
- Minimum recommended sample: 100 rows (at least 10× the k_neighbours parameter).
- FPR at defaults (k=20, contamination=0.1) on clean data: ~10%.
- FPR at defaults on heavy-tailed data: ~10–15%.

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Normal | (default) | (default) | STAT_SCALES defaults |
| Heavy-tailed (revenue, latency) | (default) | (default) | LOF is distribution-agnostic |
| Sparse / high-null | N/A | N/A | Impute nulls before use |
