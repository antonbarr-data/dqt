# `outliers_uni.iqr_fence`

> *Outlier fraction (IQR)* — flags the fraction of values outside the classic Tukey IQR inner fences `[Q1 − k·IQR, Q3 + k·IQR]`.

## What it does

Computes the first and third quartiles (Q1, Q3) and the interquartile range (IQR = Q3 − Q1) from the reference window. Lower and upper fences are defined as `Q1 − k·IQR` and `Q3 + k·IQR` respectively. At `score` time, the fraction of current values falling outside these fences is returned. With the default `k=1.5`, the fences correspond to Tukey's "inner fences"; `k=3.0` gives the "outer fences" used for extreme outlier detection.

## When to use it

- Quick, assumption-free outlier check on any numeric column.
- When you want a fully non-parametric method with no distributional assumptions.
- Symmetric or mildly skewed data where the simple IQR rule gives acceptable false-positive rates.
- Exploratory analysis or as a sanity-check layer alongside a more powerful detector.

## When not to use it

- Strongly skewed distributions — the fence is symmetric around the median in IQR units, so the dominant tail generates excessive false positives; use `adjusted_boxplot_fraction` or `double_mad_outlier_fraction` instead.
- High-dimensional pipelines where per-column sensitivity is critical — the MAD-based methods offer a higher breakdown point and are less sensitive to cluster effects.
- Very small samples (n < 10) — Q1 and Q3 are unstable; `grubbs` is better for single-outlier detection in small samples.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `k` | `float` | `1.5` | IQR multiplier. `k=1.5` = inner fences (Tukey standard). `k=3.0` = outer fences for extreme outliers only. |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.01` (1%) |
| `fail_threshold` | `0.05` (5%) |
| `direction` | `lower_is_better` |
| `score meaning` | Fraction of values outside Tukey IQR fences (0 = no outliers, 0.20 = scale max) |

## Example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore
from dqt.adapters.duckdb import DuckDBAdapter

# fct_gigs.price_usd — quick non-parametric fence check on gig listing prices
df = pd.DataFrame({
    "price_usd": [25, 30, 28, 32, 27, 29, 31, 26, 30, 500]  # 500 is the spike
})
adapter = DuckDBAdapter.from_dataframe(df)

check = Check(
    schema_name="main",
    table_name="fct_gigs",
    column_name="price_usd",
    detector_slug="iqr_fence",
    detector_params={
        "k": 1.5,  # Tukey multiplier; 1.5 = inner fences (catches ~0.7% of normal data);
                   # raise to 3.0 to flag "far outliers" only (extreme spikes); lower to
                   # 1.0 for stricter alerting on columns with tight expected ranges
    },
)
result = Runner(MemoryStore()).run(check, adapter)
print(result.verdict)         # pass / warn / fail
print(result.plain_english)   # human-readable explanation
print(result.score)           # raw score
```

## Learn more

- 📺 [How to Find Outliers: The 1.5 x IQR Rule Explained](https://www.youtube.com/watch?v=KMxL3E8C8Sg) — explains the Tukey IQR fence construction and why the 1.5 multiplier was chosen.

## Implementation

[`packages/dqt/src/dqt/algorithms/outliers_uni/iqr_fence.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/outliers_uni/iqr_fence.py)

## Reference

- Tukey, J.W. (1977). *Exploratory Data Analysis*. Addison-Wesley. (Chapter 2: boxplots and fences.)
- `packages/dqt/src/dqt/algorithms/outliers_uni/iqr_fence.py`

## Tests

`packages/dqt/tests/algorithms/outliers_uni/test_iqr_fence.py`
