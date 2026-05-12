# `basic.numeric_mean`

> *Mean shift (σ)* — number of baseline standard deviations the current mean has drifted.

## What it checks

Computes `AVG(col)` and `STDDEV(col)` on the reference window to establish a baseline mean and standard deviation. On each run it computes the current mean and returns `|current_mean - baseline_mean| / baseline_stddev`. A score of 0.0 means no shift; a score above 2.0 triggers a warning.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | Baseline mean and stddev are fitted automatically from the reference window |

## Scale (STAT_SCALES)

| Threshold | Value |
|---|---|
| warn | 2.0 σ |
| fail | 3.0 σ |
| direction | lower_is_better |

## Example

```python
from dqt import Check, Runner, MemoryStore
from dqt.algorithms.basic.numeric import NumericMeanDetector

# NumericMeanDetector()
#   no params — learns reference mean in fit(); flags deviations beyond STAT_SCALES thresholds;
#   use min_in_range / max_in_range for hard absolute bounds

check = Check(
    schema_name="public",
    table_name="orders",
    column_name="amount",
    detector_slug="numeric_mean",
    params={},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / warn / fail
```

## Compatible with

- Great Expectations: `expect_column_mean_to_be_between`
- Soda: `avg` (with threshold)
- Elementary: `all_columns_anomalies` (mean variant)

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/numeric.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/numeric.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/numeric.py`

## When it works well

- Numeric columns where the mean is a meaningful summary statistic and you have explicit business bounds for it.
- Complements distribution checks by catching level shifts that may not be visible in the full distribution test.

## When it fails / Limitations

- Mean is sensitive to outliers — a few extreme values can move the mean outside the expected range even when the bulk of the data is healthy; consider using `median_in_range` for robust monitoring.
- Heavy-tailed columns (revenue, session duration) have means that are heavily influenced by rare extreme values; set wide bounds or use median instead.
- FPR at defaults: 0% (rule-based).
- Minimum recommended sample: 1 row.
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based, but needs wide bounds to avoid constant alerts).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Normal bounded | tight bounds | tight bounds | e.g. expected mean ± 10% |
| Heavy-tailed (revenue, latency) | wide bounds | wide bounds | Or use median_in_range instead |
| Sparse / high-null | N/A | N/A | Use null_fraction first |
