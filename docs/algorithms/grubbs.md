# `outliers_uni.grubbs`

> *Grubbs outlier (1−p)* — tests whether the single most extreme value in a normally distributed sample is a statistically significant outlier; score is `1 − p-value`.

## What it does

Computes the Grubbs statistic `G = max|xi − x̄| / s` and converts it to a two-tailed p-value using the t-distribution with `n − 2` degrees of freedom. The score returned is `1 − p_value`, so higher scores mean stronger evidence of an outlier. The `fit` step stores no baseline state — the test is self-contained and runs entirely on the current window. A score above 0.95 (p < 0.05) triggers `warn`; above 0.99 (p < 0.01) triggers `fail`. The test requires at least 3 values.

## When to use it

- Small-sample numeric columns (3 ≤ n ≤ ~100) where you need a hypothesis-test-based conclusion rather than a rate.
- When you want to flag that the single most extreme value is anomalous, with an interpretable p-value.
- Lab measurements, sensor readings, or QA checks where normality is a reasonable assumption.
- When a binary "is there an outlier?" answer is more actionable than a fraction.

## When not to use it

- Non-normal distributions — the test's p-value calibration is only valid under normality; use `mad_outlier_fraction` or `adjusted_boxplot_fraction` for skewed or heavy-tailed data.
- When multiple outliers may be present — Grubbs detects only the single most extreme value. For up to k outliers use `generalized_esd` (Rosner's test).
- Large datasets (n > 1,000) — the test is extremely sensitive at large n and will flag tiny deviations as significant; fraction-based detectors are more practical.
- When a fraction score is required for downstream alerting — the score is `1 − p`, not an outlier fraction.

## Parameters

Grubbs' test has no constructor parameters. The test is fully parametric and uses the t-distribution for critical-value computation.

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | No user-configurable parameters. |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.95` (p < 0.05) |
| `fail_threshold` | `0.99` (p < 0.01) |
| `direction` | `lower_is_better` |
| `score meaning` | `1 − p-value`; higher = stronger evidence of a single outlier (max 1.0) |

## Example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore
from dqt.adapters.duckdb import DuckDBAdapter

# fct_gigs.price_usd — small-sample check for a single anomalous gig price
df = pd.DataFrame({
    "price_usd": [25, 30, 28, 32, 27, 29, 31, 26, 30, 500]  # 500 is the spike
})
adapter = DuckDBAdapter.from_dataframe(df)

check = Check(
    schema_name="main",
    table_name="fct_gigs",
    column_name="price_usd",
    detector_slug="grubbs",
    # GrubbsDetector() takes no params; alpha=0.05 is used internally and is not
    # user-configurable — only suitable for normally distributed columns with one
    # extreme outlier; for multiple outliers use generalized_esd instead
)
result = Runner(MemoryStore()).run(check, adapter)
print(result.verdict)         # pass / warn / fail
print(result.plain_english)   # human-readable explanation
print(result.score)           # 1 - p-value
```

## Learn more

- 📺 [Grubbs Outlier Test — Introduced and Demonstrated](https://www.youtube.com/watch?v=xernlERoj-w) — introduces the Grubbs statistic, shows how the t-distribution critical value is derived, and demonstrates detection with a worked example.

## Implementation

[`packages/dqt/src/dqt/algorithms/outliers_uni/grubbs.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/outliers_uni/grubbs.py)

## Reference

- Grubbs, F.E. (1950). *Sample criteria for testing outlying observations*. Annals of Mathematical Statistics, 21(1), 27–58. https://doi.org/10.1214/aoms/1177729885
- `packages/dqt/src/dqt/algorithms/outliers_uni/grubbs.py`

## Tests

`packages/dqt/tests/algorithms/outliers_uni/test_grubbs.py`

## When it works well

- Small samples (3–100 rows) from normally distributed numeric columns (lab measurements, sensor readings, tight QA checks).
- When you need a statistically rigorous binary answer: "is the single most extreme value anomalous?" with a p-value.

## When it fails / Limitations

- Non-normal distributions — p-value calibration is only valid under normality; use `mad_outlier_fraction` for skewed or heavy-tailed data.
- Multiple outliers — Grubbs detects only the single most extreme value; masking and swamping effects occur when multiple outliers are present. Use `generalized_esd` for up to k outliers.
- Large N (> 1,000) — the test becomes over-sensitive and flags insignificant deviations; fraction-based detectors are more appropriate.
- Minimum recommended sample: 3 rows (hard minimum); 10+ rows for reliable results.
- FPR at defaults (α=0.05) on clean normal data: ~5%.
- FPR at defaults on heavy-tailed data: up to 20–30%.

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Normal | (default) | (default) | STAT_SCALES defaults |
| Heavy-tailed (revenue, latency) | N/A | N/A | Use mad_outlier_fraction instead |
| Sparse / high-null | N/A | N/A | Use null_fraction first |

## Failure modes and known limits

| Failure mode | Symptom | Fix |
|---|---|---|
| Non-normal data | Grubbs assumes normality; FPR > 10% on lognormal | Use `mad_outlier_fraction` for non-normal data |
| Masking effect | Multiple outliers suppress each other's Z-scores; GESD is the fix | Use `generalized_esd` when >1 outlier is expected |
| N < 7 | Test has no power; always returns no outlier | Collect more data |
| Multiple simultaneous outliers | Only the most extreme is tested per call | Use `generalized_esd` with `k` set to expected max outlier count |

## FPR at default alpha=0.05

| Data shape | FPR |
|---|---|
| normal(0,1) | ~5% per-test (controlled by alpha) |
| lognormal(0,1) | ~20-40% |
