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

## Source

`packages/dqt/src/dqt/algorithms/basic/numeric.py`
