# `drift.chi_square_drift`

> *Chi-square drift (1−p)* — tests whether the frequency distribution of a categorical column has shifted significantly between the reference and current windows; score = 1 − p-value.

## What it does

At fit time, records the category frequencies in the reference column as expected fractions. At score time it constructs observed counts for each known category in the current window, scales the reference fractions to a matching expected counts vector, drops zero-expected bins (unseen categories in the reference), and runs `scipy.stats.chisquare`. The score is `1 − p-value`: a score near 1 means the observed frequencies are very unlikely under the reference distribution. Categories appearing only in the current window are silently ignored (they go into the "catch-all" of zero-expected mass). The test requires at least 2 categories with non-zero expected counts.

## When to use it

- Categorical columns (status codes, country codes, product categories, device types).
- When you need a p-value-anchored drift test for categorical data.
- Monitoring label distributions in ML prediction outputs.
- When the number of categories is moderate (2–50); very high cardinality is better handled by `cramers_v`.

## When not to use it

- Numeric continuous columns — use `ks_pvalue`, `wasserstein_1`, or `psi`.
- Very small windows where expected counts < 5 per cell — the chi-square approximation breaks down; use Fisher's exact test or aggregate rare categories.
- When categories are ordered and the ordering matters — chi-square ignores order.
- When a drift *magnitude* is needed alongside the p-value — use `cramers_v` which reports Cramér's V as a bounded effect-size score.

## Parameters

This detector has no constructor parameters.

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | — |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.95` |
| `fail_threshold` | `0.99` |
| `direction` | `lower_is_better` |
| `score meaning` | `1 − p-value`; warn at p < 0.05, fail at p < 0.01 |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.drift.chi_square import ChiSquareDriftDetector

rng = np.random.default_rng(42)
# fct_reviews.rating — detect shifts in the 1-5 rating distribution on Gigler
ref_ratings = rng.choice([1, 2, 3, 4, 5], size=1000, p=[0.05, 0.10, 0.20, 0.40, 0.25])
ref = pd.DataFrame({"rating": ref_ratings.astype(str)})

# current: ratings deteriorate — 1s and 2s surge, 5s collapse
curr_ratings = rng.choice([1, 2, 3, 4, 5], size=1000, p=[0.20, 0.25, 0.25, 0.20, 0.10])
curr_drift = pd.DataFrame({"rating": curr_ratings.astype(str)})

det = ChiSquareDriftDetector()  # no params; operates directly on category counts, no binning needed;
                                # best for string columns (status, tier, category) or low-cardinality integers
state = det.fit(ref)
result = det.score(curr_drift, state)
print(result.verdict)        # fail
print(result.plain_english)  # "Chi-square test p=0.0000 — categorical drift detected"
print(result.score)          # ~1.0

curr_stable = pd.DataFrame({
    "rating": rng.choice([1, 2, 3, 4, 5], 1000, p=[0.05, 0.10, 0.20, 0.40, 0.25]).astype(str)
})
print(det.score(curr_stable, state).verdict)  # pass
```

## Learn more

- 📺 [Chi-Square Test: clearly explained](https://www.youtube.com/watch?v=YoZlIQFcggk) — explains the chi-square goodness-of-fit test, degrees of freedom, and how to read the p-value for categorical frequency comparisons.

## Implementation

[`packages/dqt/src/dqt/algorithms/drift/chi_square.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/drift/chi_square.py)

## Reference

- Pearson, K. (1900). On the criterion that a given system of deviations from the probable in the case of a correlated system of variables is such that it can be reasonably supposed to have arisen from random sampling. *Philosophical Magazine*, 50(302), 157–175.
- `packages/dqt/src/dqt/algorithms/drift/chi_square.py`

## Tests

`packages/dqt/tests/algorithms/drift/test_chi_square_drift.py`
