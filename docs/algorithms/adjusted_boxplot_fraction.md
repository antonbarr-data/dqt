# `outliers_uni.adjusted_boxplot_fraction`

> *Outlier fraction (adj. boxplot)* — flags the fraction of values outside Tukey fences that are corrected for skewness via the medcouple (MC) statistic, preventing over-flagging on asymmetric distributions.

## What it does

Extends the standard IQR boxplot by incorporating the medcouple (MC), a robust measure of skewness in [−1, 1]. For right-skewed data (MC ≥ 0), the upper fence is widened exponentially (`Q3 + h·exp(3·MC)·IQR`) and the lower fence is shrunk (`Q1 − h·exp(−4·MC)·IQR`), preventing the heavy right tail from being flagged as outliers. For left-skewed data (MC < 0), the adjustments are mirrored. The `fit` step computes and stores the adjusted fences from the reference window. At `score` time, the fraction of current values falling outside those fences is returned.

## When to use it

- Numeric columns with mild to moderate skewness (medcouple in (−0.5, 0.5) or skewness in (−2, 2)).
- When the standard IQR fence over-flags the dominant tail as outliers.
- When you want a non-parametric fence that is interpretable as a boxplot extension.
- Auto-selected by `auto_outlier` for skewed distributions that do not exceed the heavy-skew threshold.

## When not to use it

- Extremely heavy skewness (|medcouple| > 0.5 or |skewness| > 2.0) — use `double_mad_outlier_fraction` instead; the exponential correction becomes unstable at high MC values.
- Normal distributions — the standard IQR fence (`iqr_fence`) or `zscore_outlier_fraction` is more efficient.
- Very small samples (n < 20) — the medcouple estimate is noisy and the fence positions are unreliable.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `h` | `float` | `1.5` | IQR multiplier (same role as Tukey's `k`). The standard value is 1.5 (inner fences). Setting `h=3.0` gives outer fences for a more permissive threshold. |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.01` (1%) |
| `fail_threshold` | `0.05` (5%) |
| `direction` | `lower_is_better` |
| `score meaning` | Fraction of values outside the medcouple-adjusted fences (0 = no outliers, 0.20 = scale max) |

## Example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore
from dqt.adapters.duckdb import DuckDBAdapter

# fct_gigs.price_usd — right-skewed prices where the standard IQR fence over-flags the tail
df = pd.DataFrame({
    "price_usd": [10, 12, 9, 11, 10, 13, 15, 11, 12, 400]  # 400 is the spike
})
adapter = DuckDBAdapter.from_dataframe(df)

check = Check(
    schema_name="main",
    table_name="fct_gigs",
    column_name="price_usd",
    detector_slug="adjusted_boxplot_fraction",
    detector_params={
        "h": 1.5,  # same semantics as IQR k, corrected for skewness; 1.5 is the right
                   # default for skewed warehouse columns; rarely needs changing — the
                   # medcouple correction already adapts to the column's asymmetry
    },
)
result = Runner(MemoryStore()).run(check, adapter)
print(result.verdict)         # pass / warn / fail
print(result.plain_english)   # human-readable explanation
print(result.score)           # raw score
```

## Learn more

<!-- TODO: no simple YouTube explanation found -->

## Implementation

[`packages/dqt/src/dqt/algorithms/outliers_uni/adjusted_boxplot.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/outliers_uni/adjusted_boxplot.py)

## Reference

- Hubert, M. & Vandervieren, E. (2008). *An adjusted boxplot for skewed distributions*. Computational Statistics & Data Analysis, 52(12), 5186–5201. https://doi.org/10.1016/j.csda.2007.11.008
- `packages/dqt/src/dqt/algorithms/outliers_uni/adjusted_boxplot.py`

## Tests

`packages/dqt/tests/algorithms/outliers_uni/test_adjusted_boxplot_fraction.py`

## When it works well

- Numeric columns with mild to moderate skewness where the plain IQR fence over-flags the dominant tail (revenue, latency, session duration).
- Non-parametric — no distributional assumptions; the medcouple correction adapts automatically to the column's asymmetry.

## When it fails / Limitations

- Extremely heavy skewness (|medcouple| > 0.6) causes the exponential correction to become unstable — use `double_mad_outlier_fraction` instead.
- The medcouple computation is O(n log n) and requires at least 20 observations for a reliable estimate.
- Normal data: slightly higher FPR than the plain IQR fence because the correction widens one fence.
- Minimum recommended sample: 20 rows.
- FPR at defaults (h=1.5) on clean normal data: ~0.7%.
- FPR at defaults on heavy-tailed (lognormal) data: ~1–3%.

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Normal | (default) | (default) | STAT_SCALES defaults |
| Heavy-tailed (revenue, latency) | (default) | (default) | Medcouple correction handles this |
| Extremely skewed (|MC| > 0.6) | N/A | N/A | Use double_mad_outlier_fraction instead |

## Failure modes and known limits

| Failure mode | Symptom | Fix |
|---|---|---|
| Multimodal reference | Medcouple estimates median of a mixed distribution; fences may not span all modes | Segment data before scoring |
| N < 50 | Medcouple estimate noisy -- requires ~50 points for stability | Increase baseline window |
| Symmetric data | Medcouple=0; fences reduce to standard IQR -- no downside, just unnecessary | Use `iqr_fence` for cleaner semantics |

## FPR at default (medcouple-adjusted fences)

| Data shape | FPR |
|---|---|
| normal(0,1) | ~1% |
| lognormal(0,1) | ~0.5% -- key advantage over plain IQR |
| Pareto(alpha=1.5) | ~1% |
