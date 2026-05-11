# `outliers_multi.one_class_svm`

> *Outlier fraction (OC-SVM)* — learns a tight decision boundary around the reference distribution using a kernel-based Support Vector Machine, then flags current rows that fall outside that boundary.

## What it does

At fit time the detector trains a `sklearn.svm.OneClassSVM` on the numeric columns of the reference DataFrame. The RBF kernel maps points into a high-dimensional feature space where the algorithm finds the smallest hypersphere (or half-space, controlled by the kernel) enclosing at least `1 − ν` of the training mass. At score time, rows that the fitted model classifies as `−1` (outside the learned support) are counted as outliers. The score is the fraction of such rows in the current window.

## When to use it

- Complex, non-convex reference distributions where Mahalanobis distance (which assumes an ellipsoidal boundary) would miss outliers along the margins.
- Detecting gig listings or booking patterns that deviate from a multi-modal reference — e.g. normal $10 and $200 price clusters, but nothing in between; OC-SVM can model both modes simultaneously.
- When a soft, kernel-defined boundary is preferable to axis-aligned histogram bins (`hbos`) or a local density estimate (`lof`).
- Moderate-dimensional data (2–30 features) with enough reference data to fit the kernel matrix (≥ 300 rows).

## When not to use it

- Very high dimensions (> 50 features) — the RBF kernel requires choosing `γ` carefully and the SVM's kernel matrix becomes expensive; use `ecod` instead.
- Large datasets (> 100 k rows) — training complexity is O(n²–n³) in the number of support vectors; sub-sample or switch to `isolation_forest_fraction`.
- When `ν` is meant to be a hard outlier-rate guarantee — `ν` is an upper bound on the training outlier fraction, not an exact calibration.
- Streaming data — the model must be re-fit to incorporate new reference distributions; use `adwin` for stream-native detection.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `nu` | `float` | `0.01` | Upper bound on the fraction of training points that can be outside the boundary (and lower bound on support vectors). Increase to allow a looser boundary. |
| `kernel` | `str` | `"rbf"` | Kernel function. `"rbf"` (default), `"linear"`, `"poly"`, or `"sigmoid"`. `"rbf"` is the right choice in almost all cases. |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.05` |
| `fail_threshold` | `0.10` |
| `direction` | `lower_is_better` |
| `score meaning` | Fraction of rows classified as outliers by OC-SVM; warn ≥ 5 %, fail ≥ 10 % |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.outliers_multi.one_class_svm import OneClassSVMDetector

rng = np.random.default_rng(42)
n = 2000

# Reference: two legitimate gig price/delivery clusters on Gigler
low_end  = pd.DataFrame({"price_usd": rng.normal(12, 3, n//2),
                          "delivery_days": rng.normal(5, 1, n//2)})
high_end = pd.DataFrame({"price_usd": rng.normal(200, 30, n//2),
                          "delivery_days": rng.normal(3, 0.5, n//2)})
ref = pd.concat([low_end, high_end], ignore_index=True)

# Inject anomalies: mid-range pricing that fits neither cluster
anomalous = pd.DataFrame({"price_usd": rng.normal(80, 5, 40),
                           "delivery_days": rng.normal(15, 2, 40)})
curr = pd.concat([ref.sample(500, random_state=3), anomalous], ignore_index=True)

det = OneClassSVMDetector(nu=0.01, kernel="rbf")
state = det.fit(ref)
result = det.score(curr, state)

print(result.verdict)        # warn or fail
print(result.plain_english)  # "7.3% of rows classified as outliers by One-Class SVM"
print(result.details)        # {"outlier_fraction": 0.073, "n_rows": 540}
```

## Learn more

- 📺 [One Class SVM for Anomaly Detection — Unsupervised Machine Learning](https://www.youtube.com/watch?v=0IkFnHpUUjE) — explains the intuition of fitting a boundary around normal data and classifying deviations as anomalies.

## Reference

- Schölkopf, B., Platt, J.C., Shawe-Taylor, J., Smola, A.J., & Williamson, R.C. (2001). Estimating the support of a high-dimensional distribution. *Neural Computation*, 13(7), 1443–1471.
- `packages/dqt/src/dqt/algorithms/outliers_multi/one_class_svm.py`

## Tests

`packages/dqt/tests/algorithms/outliers_multi/test_one_class_svm.py`
