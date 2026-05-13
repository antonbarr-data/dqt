# `info.cramers_v`

> *Cramér's V (drift)* — measures the strength of categorical drift by building a 2 × K contingency table (reference vs. current) and reporting Cramér's V as a normalised association coefficient; score ∈ [0, 1].

## What it does

At fit time, records the value counts of the reference column. At score time it constructs a 2 × K contingency table (one row for reference counts, one for current counts across all K reference categories), runs `scipy.stats.chi2_contingency` to obtain χ², and computes V = √(χ² / (n × (min(rows, cols) − 1))). With 2 rows, min(rows, cols) − 1 = 1, so V = √(χ² / n). The result is clamped to [0, 1]: 0 means the relative frequency distributions are identical, 1 means they are maximally different. Unlike `chi_square_drift`, V is an effect-size measure rather than a test statistic, making it comparable across columns with different numbers of categories and different sample sizes.

## When to use it

- Categorical columns where you want a normalised drift *magnitude* rather than a p-value.
- Comparing drift intensity across multiple categorical columns on a common [0, 1] scale.
- Summarising categorical drift in dashboard KPIs or stat gauge banks.
- When `chi_square_drift` signals drift but you want to quantify how severe it is.

## When not to use it

- When a p-value is the required output — use `chi_square_drift` instead.
- Numeric continuous columns — use `ks_pvalue`, `wasserstein_1`, or `psi`.
- Very small windows (< 30 per category) — chi² approximation is unreliable and V is noisy.
- Binary columns with highly imbalanced classes — V can be inflated; interpret alongside absolute count differences.

## Parameters

This detector has no constructor parameters.

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | — |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.15` |
| `fail_threshold` | `0.30` |
| `direction` | `lower_is_better` |
| `score meaning` | Cramér's V ∈ [0, 1]; 0 = no drift, 0.15 = moderate drift, 0.3+ = strong drift |

## Example

```python
import pandas as pd
import numpy as np
from dqt.algorithms.info.cramers_v import CramersVDetector

rng = np.random.default_rng(42)
# dim_sellers.tier vs fct_reviews.rating — measure drift in seller tier distribution
# (here: tier is the categorical column being monitored)
ref_tiers = rng.choice(["bronze", "silver", "gold"], size=2000, p=[0.60, 0.30, 0.10])
ref = pd.DataFrame({"tier": ref_tiers})

# current: gold sellers surge (tier upgrade campaign ran last month)
curr_tiers = rng.choice(["bronze", "silver", "gold"], size=2000, p=[0.40, 0.35, 0.25])
curr_drift = pd.DataFrame({"tier": curr_tiers})

det = CramersVDetector()  # no params; always pass col_a and col_b as keyword arguments
                           # to Check or directly to the detector
state = det.fit(ref)
result = det.score(curr_drift, state)
print(result.verdict)        # warn or fail
print(result.plain_english)  # "Cramér's V = 0.2341 — categorical drift"
print(result.score)          # ~0.23

# stable window — same tier distribution as reference
curr_stable = pd.DataFrame({
    "tier": rng.choice(["bronze", "silver", "gold"], 2000, p=[0.60, 0.30, 0.10])
})
print(det.score(curr_stable, state).verdict)  # pass
```

## Learn more

- 📺 [How to Calculate Cramer's V](https://www.youtube.com/watch?v=ckX8w7lWtGQ) — shows step-by-step how to build the contingency table, compute chi-square, and normalise to obtain Cramér's V as a bounded effect size.

## Implementation

[`packages/dqt/src/dqt/algorithms/info/cramers_v.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/info/cramers_v.py)

## Reference

- Cramér, H. (1946). *Mathematical Methods of Statistics*. Princeton University Press. (§21.6)
- `packages/dqt/src/dqt/algorithms/info/cramers_v.py`

## Tests

`packages/dqt/tests/algorithms/info/test_cramers_v.py`

## When it works well

- Categorical-categorical association monitoring — Cramér's V measures the strength of association between two nominal variables.
- Useful for detecting when a categorical column's relationship with another categorical column changes over time.

## When it fails / Limitations

- Continuous columns — Cramér's V requires categorical data; binning continuous data introduces arbitrary choices that affect the result. Use `mutual_information` for mixed or continuous pairs.
- Small samples produce upward-biased Cramér's V estimates — the bias-corrected variant (Tschuprow or bias-corrected V) should be used for N < 200.
- High-cardinality columns produce sparse contingency tables, inflating V; consider grouping rare categories.
- Minimum recommended sample: 50 rows (5 expected per cell in the contingency table).
- FPR at defaults on independent categorical columns: ~5% (chi-squared based).
- FPR at defaults on heavy-tailed data: N/A (categorical).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Low-cardinality categorical | (default) | (default) | STAT_SCALES defaults |
| High-cardinality categorical | 0.05 | 0.10 | Many cells inflate V; raise threshold |
| Sparse / high-null | N/A | N/A | Use null_fraction first |

## Failure modes and known limits

Cramér's V is computed from a chi-squared statistic and inherits chi-squared's known sensitivities. The biggest practical risk is small samples and sparse contingency tables, which produce upward-biased V estimates. The detector uses bias-corrected V (Bergsma 2013 correction) by default, which substantially reduces this bias but does not eliminate it entirely.

| Failure mode | Symptom | Fix |
|---|---|---|
| Small N (< 50) | V is upward-biased even after correction; warns on distributions that haven't drifted | Require N >= 50 per window; reduce check frequency or increase window size |
| High-cardinality column (> 50 distinct values) | Many low-count cells inflate chi-squared and therefore V | Group rare categories into an "other" bucket before running the check |
| Unseen categories in current window | Current window has a category not in the reference; chi-squared has a zero cell for that category | Use `chi_square_drift` with `handle_unseen=add_small_count` option; unseen categories always indicate drift |
| Reference and current have very different N | V is sensitive to minimum N; asymmetric window sizes inflate V | Subsample to equal sizes before comparing |
| Binary column with heavy class imbalance | V overstates drift when the minority class shifts; absolute count change is small | Report alongside absolute count differences; check rare-class shift separately |

### FPR by sample size

| N per window | Expected FPR (no drift, 5-category column) | Notes |
|---|---|---|
| 30 | ~15% | Bias correction insufficient at this N |
| 100 | ~7% | Approaching correct calibration |
| 500 | ~5% | Well-calibrated |
| 1000+ | ~5% | Stable at nominal alpha |

### Threshold recommendations

- Default warn=0.15 / fail=0.30 is calibrated for moderate-cardinality (5-20 values) columns with N >= 200.
- For high-cardinality columns (> 50 values): raise thresholds to warn=0.05 / fail=0.10 to account for elevated baseline V.
- For binary columns: use `chi_square_drift` instead, which gives a direct p-value without the normalisation artefacts of V.
