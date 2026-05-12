# `basic.null_fraction`

> *Null fraction* — fraction of rows where the column value is NULL.

## What it checks

Counts the number of NULL values in the column and divides by the total row count. A score of 0.0 means no nulls; 1.0 means every value is null. No baseline is required — the check is threshold-based.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | Stateless; all config is on the Check definition itself |

## Scale (STAT_SCALES)

| Threshold | Value |
|---|---|
| warn | 0.01 (1% null) |
| fail | 0.05 (5% null) |
| direction | lower_is_better |

## Example

```python
from dqt import Check, Runner, MemoryStore
from dqt.algorithms.basic.null_fraction import NullFractionDetector

# NullFractionDetector()
#   no params — thresholds set via STAT_SCALES (warn at >1%, fail at >5% by default)
#   override per-check in YAML with `fail_if: "> 0.001"` for critical columns

check = Check(
    schema_name="public",
    table_name="orders",
    column_name="customer_id",
    detector_slug="null_fraction",
    params={},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / warn / fail
```

## Compatible with

- Great Expectations: `expect_column_values_to_not_be_null`
- Soda: `missing_percent`

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/null_fraction.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/null_fraction.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/null_fraction.py`

## When it works well

- Any column type. Stateless — no reference window needed.
- Stable columns (IDs, required fields) where even 1% null is an incident.

## When it fails / Limitations

- Structural nulls (nullable FK columns, optional attributes) will always fire at the default 1% warn threshold. Set per-check thresholds for those columns.
- Does not distinguish intentional nulls (explicit `NULL`) from missing data (ETL failure).
- FPR at defaults: 0% (rule-based, no statistical approximation).
- Minimum recommended sample: 1 row.
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based).

## Recommended thresholds by data shape

| Column type | warn | fail | Notes |
|---|---|---|---|
| Critical ID / required field | 0.001 | 0.01 | Near-zero tolerance |
| Optional attributes | 0.05 | 0.20 | Structural nulls expected |
| Default | 0.01 | 0.05 | STAT_SCALES default |
