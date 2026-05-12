# `basic.completeness`

> *Completeness* — fraction of non-null values; complement of `null_fraction`.

## What it checks

Computes `1 - (null_count / total_count)`. A score of 1.0 means all values are present; 0.0 means the column is entirely null. Fits a baseline completeness rate on the reference window and reports both current and baseline in the plain-English output.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | Threshold-based; baseline completeness is recorded for display only |

## Scale (STAT_SCALES)

| Threshold | Value |
|---|---|
| warn | 0.95 (below 95% complete) |
| fail | 0.90 (below 90% complete) |
| direction | higher_is_better |

## Example

```python
from dqt import Check, Runner, MemoryStore
from dqt.algorithms.basic.completeness import CompletenessDetector

# CompletenessDetector()
#   no params — inverse of null_fraction; score = fraction of non-null values (1.0 = fully complete)

check = Check(
    schema_name="public",
    table_name="orders",
    column_name="email",
    detector_slug="completeness",
    params={},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / warn / fail
```

## Compatible with

- Great Expectations: `expect_column_values_to_not_be_null`
- Soda: `missing_percent` (inverse)

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/completeness.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/completeness.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/completeness.py`

## When it works well

- Any column or dataset where "completeness" (fraction of non-null, non-empty values) is a defined data quality SLA.
- Complements `null_fraction` — completeness = 1 − null_fraction for simple nullability, but may also count empty strings as incomplete.

## When it fails / Limitations

- Structural incompleteness (optional attributes, sparse FK columns) will always fire at default thresholds; calibrate per-column.
- Does not detect semantically incomplete values (e.g. placeholder "N/A" strings) — use `validity` or `regex_match` for those.
- FPR at defaults: 0% (rule-based).
- Minimum recommended sample: 1 row.
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Required field | 0.001 | 0.01 | Near-zero tolerance |
| Optional field | 0.05 | 0.20 | Structural incompleteness expected |
| Sparse / high-null | N/A | N/A | Use null_fraction for granular control |

## Failure modes and known limits

| Failure mode | Symptom | Fix |
|---|---|---|
| Table truncation | Row count drops to near-zero; completeness fires on total row count | Pair with a row-count check (`null_fraction` on a surrogate PK column) |
| Partial nulls vs full nulls | Completeness measures non-null fraction; a column may be partially populated by design | Set `min_completeness` to reflect expected fill rate per column |
