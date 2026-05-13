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

## Failure modes and known limits

`numeric_mean` reports a Z-score: how many baseline standard deviations the current mean has moved. The check inherits the well-known over-sensitivity of Z-score monitors on non-Gaussian data and the masking problem when outliers are present in the reference.

| Failure mode | Symptom | Fix |
|---|---|---|
| Outliers in reference inflate baseline stddev | The baseline stddev is large, so real mean shifts score below 2.0 and go undetected | Use a robust baseline: fit on a cleaned reference window with outliers removed |
| Outliers in current inflate current mean | One large transaction moves the mean outside the band even though the bulk of data is healthy | Switch to `median_in_range` for heavy-tailed columns |
| Seasonal mean drift | The mean drifts seasonally but is not a real data quality issue | Re-fit baseline seasonally; or use a drift detector (`ks_pvalue`, `wasserstein_1`) that compares same-period windows |
| Near-zero baseline stddev | If stddev approaches zero (near-constant column), the Z-score becomes infinite for any deviation | Add a minimum stddev guard; use `value_in_range` for near-constant columns |
| Small current window (< 30 rows) | Sample mean has high variance; the Z-score fires on noise | Require N >= 30 per current window; or widen thresholds for small-batch tables |

### FPR calibration table

| Data shape | Expected FPR at warn=2.0 sigma | Notes |
|---|---|---|
| Normal(0,1) | ~4.6% | Theoretical two-sided 2-sigma FPR |
| Lognormal(0,1) (typical revenue) | ~8-12% | Right-skew inflates upward false positives |
| Poisson(lambda=10) | ~5% | Approximately normal for large lambda |
| Pareto(1.5) | ~15-20% | Heavy tail; mean is volatile; use median instead |

### Threshold recommendations

- Default warn=2.0 sigma / fail=3.0 sigma is calibrated for near-Gaussian columns.
- For heavy-tailed columns: use `median_in_range` instead; `numeric_mean` will generate excessive alerts.
- Re-fit the baseline whenever there is a known planned change to the mean (e.g. a pricing update, a new product launch).
