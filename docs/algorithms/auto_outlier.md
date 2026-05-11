# `outliers_uni.auto_outlier`

> *Auto outlier (adaptive)* — automatically profiles the reference distribution and delegates to the statistically appropriate univariate outlier detector, eliminating the need to pre-select a method.

## What it does

At `fit` time, the detector calls `classify_distribution` to characterise the reference column (normal, skewed, heavy-tailed, multimodal, uniform, or unknown). It then selects the best-fit slug from the registry using this decision table:

| Distribution type | Selected detector |
|---|---|
| Normal | `zscore_outlier_fraction` |
| Skewed (heavy: \|MC\| > 0.5 or \|skewness\| > 2.0) | `double_mad_outlier_fraction` |
| Skewed (moderate) | `adjusted_boxplot_fraction` |
| Heavy-tailed | `mad_outlier_fraction` |
| Multimodal | `mad_outlier_fraction` |
| Uniform | IQR fences + `needs_hitl=true` flag |
| Unknown | `mad_outlier_fraction` |

The selected detector's `fit` result is stored alongside the distribution profile. At `score` time, the same inner detector is instantiated and called with the stored state. For uniform distributions, IQR fences are applied but the verdict is forced to `warn` and `needs_hitl=true` is set in `details`, because there is no statistical basis for outlier thresholds on uniform data.

## When to use it

- As the default check for any new numeric column where the distribution shape is unknown.
- CI pipelines where you want automated method selection without manual per-column configuration.
- When dataset schema evolves frequently and you cannot maintain per-column detector choices.

## When not to use it

- When you have domain knowledge about the distribution and want the guarantee of a specific method — pick the method directly for reproducibility and auditability.
- Uniform columns — `auto_outlier` will always produce a `warn` verdict with a HITL flag; review and configure an appropriate check manually.
- When detector stability across runs is critical (e.g. regulated environments) — distribution re-classification at `fit` could select a different inner detector after a data shift, changing the score's meaning.

## Parameters

No constructor parameters. The inner detector is selected automatically; its default parameters are used.

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | Distribution profiling and method selection are fully automatic. |

## Scale (STAT_SCALES)

`auto_outlier` delegates its score and verdict to the selected inner detector. Consult the scale for that detector (`mad_outlier_fraction`, `double_mad_outlier_fraction`, `adjusted_boxplot_fraction`, or `zscore_outlier_fraction`). The `details` dict always includes `auto_selected_method` and `distribution_type` for transparency.

| Field | Value |
|---|---|
| `warn_threshold` | Inherited from selected inner detector |
| `fail_threshold` | Inherited from selected inner detector |
| `direction` | `lower_is_better` |
| `score meaning` | Outlier fraction, as reported by the selected inner detector |

## Example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore
from dqt.adapters.duckdb import DuckDBAdapter

# fct_gigs.price_usd — distribution shape unknown; auto_outlier selects the right method
df = pd.DataFrame({
    "price_usd": [25, 30, 28, 32, 27, 29, 31, 26, 30, 999]  # 999 is the spike
})
adapter = DuckDBAdapter.from_dataframe(df)

check = Check(
    schema_name="main",
    table_name="fct_gigs",
    column_name="price_usd",
    detector_slug="auto_outlier",
    # AutoOutlierDetector() takes no params; the inner detector and its default
    # parameters are selected automatically based on the distribution profile;
    # result.details["auto_selected_method"] shows which detector was chosen
)
result = Runner(MemoryStore()).run(check, adapter)
print(result.verdict)                              # pass / warn / fail
print(result.plain_english)                        # human-readable explanation
print(result.score)                                # raw score
print(result.details["auto_selected_method"])      # which detector was chosen
print(result.details["distribution_type"])         # classified distribution type
```

## Learn more

<!-- TODO: no simple YouTube explanation found -->

## Implementation

[`packages/dqt/src/dqt/algorithms/outliers_uni/auto_outlier.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/outliers_uni/auto_outlier.py)

## Reference

- Hubert, M. & Vandervieren, E. (2008). *An adjusted boxplot for skewed distributions*. Computational Statistics & Data Analysis, 52(12), 5186–5201.
- Leys, C. et al. (2013). *Detecting outliers: Do not use standard deviation around the mean, use absolute deviation around the median*. Journal of Experimental Social Psychology, 49(4), 764–766.
- `packages/dqt/src/dqt/algorithms/outliers_uni/auto_outlier.py`

## Tests

`packages/dqt/tests/algorithms/outliers_uni/test_auto_outlier.py`
