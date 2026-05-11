# `outliers_uni.double_mad_outlier_fraction`

> *Outlier fraction (double-MAD)* — flags the fraction of outliers using an asymmetric MAD that applies separate scale estimates to the left and right sides of the median, making it robust on skewed distributions.

## What it does

Extends the modified Z-score approach by computing two MADs: `MAD_left` (median of |xi − median| for values at or below the median) and `MAD_right` (for values at or above the median). At `score` time, each value's modified Z-score uses the side-appropriate MAD — `MAD_left` for values below the median, `MAD_right` for values above it. Multiplying by the consistency factor `0.6745` preserves the interpretation of the threshold in standard-deviation units. The reference `fit` step records the median and both half-MADs from the baseline window; `score` computes the fraction of current values exceeding `threshold`.

## When to use it

- Numeric columns with a skewed or asymmetric distribution (e.g. transaction amounts, latencies, file sizes).
- When the right tail is much heavier than the left (or vice versa) and a symmetric MAD would inflate the threshold on the lighter side.
- Preferred over `adjusted_boxplot_fraction` when medcouple exceeds 0.5 or skewness exceeds 2.0 (auto-selected by `auto_outlier`).
- When breakdown-point robustness (50%) is required alongside asymmetric sensitivity.

## When not to use it

- Symmetric or near-normal data — plain `mad_outlier_fraction` is sufficient and slightly more efficient.
- Distributions with so few values below (or above) the median that `MAD_left` or `MAD_right` is estimated from fewer than ~10 points.
- Categorical or ordinal columns where the concept of side-specific deviation is not meaningful.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `threshold` | `float` | `3.5` | Modified Z-score cutoff. Values on either side whose side-adjusted modified Z exceeds this are counted as outliers. |

## Scale (STAT_SCALES)

| Field | Value |
|---|---|
| `warn_threshold` | `0.01` (1%) |
| `fail_threshold` | `0.05` (5%) |
| `direction` | `lower_is_better` |
| `score meaning` | Fraction of values flagged by the asymmetric double-MAD rule (0 = no outliers, 0.20 = scale max) |

## Example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore
from dqt.adapters.duckdb import DuckDBAdapter

# Right-skewed revenue column with a high-end outlier
df = pd.DataFrame({"revenue": [50, 52, 49, 55, 48, 60, 54, 51, 53, 5000]})
adapter = DuckDBAdapter.from_dataframe(df)

check = Check(
    schema_name="main",
    table_name="data",
    column_name="revenue",
    detector_slug="double_mad_outlier_fraction",
)
result = Runner(MemoryStore()).run(check, adapter)
print(result.verdict)         # pass / warn / fail
print(result.plain_english)   # human-readable explanation
print(result.score)           # raw score
```

## Reference

- Rousseeuw, P.J. & Croux, C. (1993). *Alternatives to the Median Absolute Deviation*. Journal of the American Statistical Association, 88(424), 1273–1283.
- Leys, C. et al. (2013). *Detecting outliers: Do not use standard deviation around the mean, use absolute deviation around the median*. Journal of Experimental Social Psychology, 49(4), 764–766.
- `packages/dqt/src/dqt/algorithms/outliers_uni/mad.py`

## Tests

`packages/dqt/tests/algorithms/outliers_uni/test_double_mad_outlier_fraction.py`
