# `basic.volume`

> *Row-count change* — fractional deviation of the current row count from the baseline.

## What it checks

Counts rows in the current window, compares to the baseline count fitted from the reference window, and reports `|current / baseline - 1|`. A score of 0.0 means row count is identical to baseline; 0.25 means it has drifted 25% in either direction. Useful for detecting pipeline failures, accidental truncations, or unexpected data surges.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | Baseline row count is fitted automatically from the reference window |

## Scale (STAT_SCALES)

| Threshold | Value |
|---|---|
| warn | 0.10 (10% deviation) |
| fail | 0.25 (25% deviation) |
| direction | lower_is_better |

## Example

```python
from dqt import Check, Runner, MemoryStore

check = Check(
    schema_name="public",
    table_name="fct_orders",
    detector_slug="volume",
    params={},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / warn / fail
```

## Compatible with

- Great Expectations: `expect_table_row_count_to_be_between`
- Soda: `row_count` (with anomaly detection)
- Elementary: `volume_anomaly`

## Source

`packages/dqt/src/dqt/algorithms/basic/volume.py`
