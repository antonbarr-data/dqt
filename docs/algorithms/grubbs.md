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

# Sample data with an outlier
df = pd.DataFrame({"amount": [100, 102, 98, 101, 99, 103, 500]})  # 500 is the spike
adapter = DuckDBAdapter.from_dataframe(df)

check = Check(
    schema_name="main",
    table_name="data",
    column_name="amount",
    detector_slug="grubbs",
)
result = Runner(MemoryStore()).run(check, adapter)
print(result.verdict)         # pass / warn / fail
print(result.plain_english)   # human-readable explanation
print(result.score)           # 1 - p-value
```

## Reference

- Grubbs, F.E. (1950). *Sample criteria for testing outlying observations*. Annals of Mathematical Statistics, 21(1), 27–58. https://doi.org/10.1214/aoms/1177729885
- `packages/dqt/src/dqt/algorithms/outliers_uni/grubbs.py`

## Tests

`packages/dqt/tests/algorithms/outliers_uni/test_grubbs.py`
