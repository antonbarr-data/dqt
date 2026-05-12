# `outliers_uni.generalized_esd`

> *Outlier fraction (GESD)* — detects up to k outliers in a normally distributed sample using Rosner's Generalized Extreme Studentized Deviate (ESD) test; score is the fraction of outliers found.

## What it does

Iteratively removes the value with the largest |xi − x̄| / s, computing a critical lambda value from the t-distribution at each step. The number of outliers found is the largest `i` for which the test statistic `Ri` exceeds `λi`. Up to `max_outliers` candidates are tested in a single pass; the default auto-mode tests up to `max(10, n // 10)` candidates. The score returned is `n_outliers / n` — the fraction of the sample identified as outliers. The test requires at least 6 values. The `fit` step stores no baseline state; the test is applied entirely to the current window.

## When to use it

- Numeric columns that are approximately normal and may contain multiple simultaneous outliers.
- When you need a statistically rigorous multi-outlier test with controlled Type I error (`alpha`).
- Audit and financial data where a precise count of anomalous records is required.
- When Grubbs is insufficient because you suspect more than one outlier is present.

## When not to use it

- Non-normal distributions — the critical values are derived from the t-distribution and are only valid under normality; use `double_mad_outlier_fraction` or `adjusted_boxplot_fraction` for skewed data.
- Very small samples (n < 6) — the implementation returns `pass` with score 0.0; the test is not defined for fewer than 6 observations.
- Very large datasets (n > 100,000) — the iterative removal is O(k·n) and becomes expensive; `mad_outlier_fraction` is more scalable and nearly as powerful.
- When you want a score on a continuous scale rather than a count-derived fraction.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `max_outliers` | `int` | `0` | Maximum number of outliers to test for. `0` = auto: `max(10, n // 10)`. Set explicitly to cap the search and reduce computation. |
| `alpha` | `float` | `0.05` | Significance level for each individual ESD test. Controls the family-wise Type I error across the `max_outliers` tests. |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.01` (1%) |
| `fail_threshold` | `0.05` (5%) |
| `direction` | `lower_is_better` |
| `score meaning` | Fraction of values identified as outliers by GESD (0 = none, 0.10 = scale max) |

## Example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore
from dqt.adapters.duckdb import DuckDBAdapter

# fct_gigs.price_usd — detect multiple anomalous gig prices in one pass
df = pd.DataFrame({
    "price_usd": [25, 30, 28, 32, 27, 29, 31, 26, 30, 500, 450]  # 500 and 450 are spikes
})
adapter = DuckDBAdapter.from_dataframe(df)

check = Check(
    schema_name="main",
    table_name="fct_gigs",
    column_name="price_usd",
    detector_slug="generalized_esd",
    detector_params={
        "max_outliers": 0,   # 0 = auto (max(10, n // 10)); set to ~1% of expected row
                             # count (e.g. 10 for 1000 rows) to cap search and reduce
                             # computation on large datasets
        "alpha": 0.05,       # significance level; 0.05 is standard; lower to 0.01 to
                             # reduce false positives in low-noise regulated pipelines
    },
)
result = Runner(MemoryStore()).run(check, adapter)
print(result.verdict)         # pass / warn / fail
print(result.plain_english)   # human-readable explanation
print(result.score)           # raw score (outlier fraction)
```

## Learn more

<!-- TODO: no simple YouTube explanation found -->

## Implementation

[`packages/dqt/src/dqt/algorithms/outliers_uni/grubbs.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/outliers_uni/grubbs.py)

## Reference

- Rosner, B. (1983). *Percentage Points for a Generalized ESD Many-Outlier Procedure*. Technometrics, 25(2), 165–172. https://doi.org/10.2307/1268549
- `packages/dqt/src/dqt/algorithms/outliers_uni/grubbs.py`

## Tests

`packages/dqt/tests/algorithms/outliers_uni/test_generalized_esd.py`

## When it works well

- Numeric columns with approximately normal distributions where up to k outliers may be present simultaneously.
- Extends Grubbs for multiple-outlier scenarios (masking prevention) — ideal for small-to-medium samples (10–500 rows).

## When it fails / Limitations

- Assumes normality — fails on heavy-tailed or skewed distributions (same limitation as Grubbs); use `mad_outlier_fraction` or `double_mad_outlier_fraction` instead.
- Requires specifying k (maximum number of outliers) in advance; if k is set too low, masking still occurs.
- Computationally O(k·n) — acceptable for typical warehouse sample sizes but do not set k > 20.
- Minimum recommended sample: 10 rows plus 2× the expected k.
- FPR at defaults (α=0.05, k=10) on clean normal data: ~5% across all k tests; Bonferroni-style sequential control reduces overall FPR.
- FPR at defaults on heavy-tailed data: 15–30%.

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Normal | (default) | (default) | STAT_SCALES defaults |
| Heavy-tailed (revenue, latency) | N/A | N/A | Use mad_outlier_fraction instead |
| Sparse / high-null | N/A | N/A | Use null_fraction first |
