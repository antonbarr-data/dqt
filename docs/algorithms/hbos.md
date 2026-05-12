# `outliers_multi.hbos`

> *Outlier fraction (HBOS)* — assigns each row an anomaly score equal to the sum of log-inverse bin frequencies across all numeric columns, then reports the fraction of current rows above the reference 99th-percentile score.

## What it does

At fit time the detector builds a per-column histogram with `n_bins` equal-width bins over the reference DataFrame and records the bin frequencies. The HBOS score for a row is `Σⱼ log(1 / freq(xⱼ in binⱼ))` — points landing in rare histogram bins accumulate high scores. The 99th-percentile score over the reference is stored as the threshold. At score time each current row is mapped to the same bins and its HBOS score is computed; the fraction exceeding the stored threshold is the detector's score. Laplace smoothing (`ε = 1e-6`) prevents division by zero for unseen bins.

## When to use it

- High-throughput pipelines where inference speed matters — HBOS scores rows in O(n × d) with no kernel matrix or nearest-neighbour lookups.
- Wide tables (many numeric columns) where neighbor-based detectors (`lof`, `one_class_svm`) are too slow.
- Detecting gig listings or bookings with unusual combinations of price, rating, and delivery characteristics when the features are approximately independent.
- Quick first-pass anomaly filter before a more expensive detector confirms hits.

## When not to use it

- Strongly correlated features — HBOS treats each dimension independently (like a Naive Bayes assumption), so it misses correlational anomalies that Mahalanobis or LOF would catch.
- Very few bins relative to the data range — HBOS is sensitive to `n_bins`; too few bins lose resolution, too many create sparse bins that inflate scores for inliers.
- When the distribution shifts significantly at test time in a way that unseen bins are common — HBOS scores unseen bins at their smoothed minimum, which can mask genuine outliers.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `n_bins` | `int` | `20` | Number of equal-width histogram bins per column. Increase for higher-resolution distributions; the rule of thumb is roughly √n for n reference rows. |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.05` |
| `fail_threshold` | `0.10` |
| `direction` | `lower_is_better` |
| `score meaning` | Fraction of rows with HBOS score above the reference 99th-percentile threshold; warn ≥ 5 %, fail ≥ 10 % |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.outliers_multi.hbos import HBOSDetector

rng = np.random.default_rng(42)
n = 5000

# Reference Gigler gig listing features
ref = pd.DataFrame({
    "price_usd":   rng.lognormal(mean=3.2, sigma=0.7, size=n),
    "rating_avg":  rng.uniform(3.5, 5.0, size=n),
})

# Inject anomalies: suspiciously cheap + suspiciously high rating
anomalous = pd.DataFrame({
    "price_usd":   [1.0, 1.5, 2.0, 1.0, 1.5],
    "rating_avg":  [5.0, 5.0, 5.0, 4.99, 4.98],
})
curr = pd.concat([ref.sample(1000, random_state=9), anomalous], ignore_index=True)

det = HBOSDetector(
    n_bins=20,  # histogram bins per column; 20 is a good default for columns with 1k–100k distinct values;
                # increase to 50 for high-cardinality continuous columns;
                # decrease to 10 for low-cardinality or sparse columns
)
state = det.fit(ref)
result = det.score(curr, state)

print(result.verdict)        # warn or fail
print(result.plain_english)  # "0.5% of rows with HBOS score above reference 99th percentile"
print(result.details)        # {"outlier_fraction": 0.005, "score_threshold": ...}
```

## Learn more

- 📺 [Histogram Based Outlier Score HBOS](https://www.youtube.com/watch?v=gE1LDHB3ImQ) — walks through the histogram construction and log-inverse scoring formula with worked examples.

## Implementation

[`packages/dqt/src/dqt/algorithms/outliers_multi/hbos.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/outliers_multi/hbos.py)

## Reference

- Goldstein, M. & Dengel, A. (2012). Histogram-based Outlier Score (HBOS): A fast Unsupervised Anomaly Detection Algorithm. *KI-2012: Poster and Demo Track*, 59–63.
- `packages/dqt/src/dqt/algorithms/outliers_multi/hbos.py`

## Tests

`packages/dqt/tests/algorithms/outliers_multi/test_hbos.py`

## When it works well

- High-dimensional tabular datasets — HBOS assumes feature independence and scores each column with a histogram, making it very fast (O(n·d)) for large feature sets.
- Good baseline multivariate detector when you want interpretable per-feature anomaly contributions.

## When it fails / Limitations

- Correlated features — the independence assumption means HBOS misses anomalies that only appear in correlated pairs; use `mahalanobis_distance` or `isolation_forest_fraction` for correlated columns.
- Sparse bins in high-cardinality columns inflate scores; the bin count choice strongly affects results.
- Not suitable for categorical columns without ordinal meaning — requires numeric features.
- Minimum recommended sample: 100 rows.
- FPR at defaults (contamination=0.1) on clean data: ~10%.
- FPR at defaults on heavy-tailed data: ~12–18%.

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Normal | (default) | (default) | STAT_SCALES defaults |
| Heavy-tailed (revenue, latency) | (default) | (default) | HBOS adapts via histogram |
| Sparse / high-null | N/A | N/A | Impute nulls before use |

## Failure modes and known limits

| Failure mode | Symptom | Fix |
|---|---|---|
| Assumes feature independence | HBOS histograms each feature independently; correlated features are not captured | Use Mahalanobis or LOF when feature correlations matter |
| Bin count sensitivity | Default bin count may miss narrow anomaly peaks | Set `n_bins` to sqrt(n) as a rule of thumb |
| Fast but approximate | HBOS is a speed/accuracy trade-off | Use ECOD or LOF for higher accuracy at more compute cost |
