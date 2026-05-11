# `outliers_multi.isolation_forest_fraction`

> *Outlier fraction (IF)* — detects multivariate anomalies by measuring how easily rows can be isolated in a random forest of binary splits.

## What it does

Fits a scikit-learn `IsolationForest` on the numeric columns of the reference dataset. At score time it applies the same model to the current window and returns the fraction of rows that the model classifies as anomalies (prediction == -1). A single contamination parameter controls the threshold between inlier and outlier, set during fit. The score is dimensionless — it is a fraction in [0, 1].

## When to use it

- Multi-column tables where anomalies emerge from unusual feature *combinations* rather than any single outlier column.
- High-dimensional feature vectors (model embeddings, aggregated session features, wide fact tables).
- As a complement to univariate outlier detectors when you suspect coordinated anomalies.
- When you want a non-parametric detector with no distributional assumptions.

## When not to use it

- Single-column series — prefer `mad_outlier_fraction` or `zscore_outlier_fraction`; Isolation Forest adds noise with one feature.
- Very small datasets (< 100 rows) — the random partition model is unreliable.
- Highly sparse or mostly-zero matrices — tree splits become degenerate; consider `LOF` or `HBOS` instead.
- When anomaly scores need a probabilistic interpretation; `contamination` is a hyperparameter, not a calibrated probability.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `contamination` | `float` | `0.05` | Expected fraction of anomalies in the reference set; controls the decision threshold inside sklearn's `IsolationForest` |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.05` |
| `fail_threshold` | `0.10` |
| `direction` | `lower_is_better` |
| `score meaning` | Fraction of rows in the current window classified as multivariate anomalies |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.outliers_multi.isolation_forest import IsolationForestDetector

rng = np.random.default_rng(42)
# fct_gigs — multivariate anomaly detection across price, average rating, and delivery days
ref = pd.DataFrame({
    "price_usd": rng.normal(50, 15, 1000),
    "rating_avg": rng.normal(4.2, 0.4, 1000),
    "delivery_days": rng.normal(3, 1, 1000),
})
# current — 8% of gigs are anomalous (unusually high price + low rating + long delivery)
curr_normal = pd.DataFrame({
    "price_usd": rng.normal(50, 15, 920),
    "rating_avg": rng.normal(4.2, 0.4, 920),
    "delivery_days": rng.normal(3, 1, 920),
})
curr_anom = pd.DataFrame({
    "price_usd": rng.normal(500, 10, 80),
    "rating_avg": rng.normal(1.5, 0.2, 80),
    "delivery_days": rng.normal(30, 2, 80),
})
curr = pd.concat([curr_normal, curr_anom], ignore_index=True)

det = IsolationForestDetector(contamination=0.05)
state = det.fit(ref)
result = det.score(curr, state)
print(result.verdict)        # warn or fail
print(result.plain_english)  # "8.0% of rows flagged as multivariate outliers by Isolation Forest"
print(result.score)          # ~0.08
```

## Learn more

- 📺 [Isolation Forest: A Tree based approach for Outlier Detection (Clearly Explained)](https://www.youtube.com/watch?v=kqAxfOPlr1U) — explains how random splits isolate anomalies faster than normal points and derives the anomaly score from average path length.

## Reference

- Liu, F. T., Ting, K. M., & Zhou, Z.-H. (2008). Isolation Forest. *ICDM 2008*, 413–422.
- `packages/dqt/src/dqt/algorithms/outliers_multi/isolation_forest.py`

## Tests

`packages/dqt/tests/algorithms/outliers_multi/test_isolation_forest_fraction.py`
