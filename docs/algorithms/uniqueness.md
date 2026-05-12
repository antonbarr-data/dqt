# `basic.uniqueness`

> *Uniqueness* — fraction of distinct values relative to total row count.

## What it checks

Computes `COUNT(DISTINCT col) / COUNT(*)`. A score of 1.0 means every value is unique; lower scores indicate duplicate values. Fits a baseline uniqueness rate on the reference window and includes it in the plain-English output.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | Threshold-based; baseline uniqueness is recorded for display only |

## Scale (STAT_SCALES)

| Threshold | Value |
|---|---|
| warn | 0.95 (below 95% unique) |
| fail | 0.80 (below 80% unique) |
| direction | higher_is_better |

## Example

```python
from dqt import Check, Runner, MemoryStore
from dqt.algorithms.basic.uniqueness import UniquenessDetector

# UniquenessDetector()
#   no params — score = COUNT(DISTINCT col) / COUNT(*) (1.0 = fully unique)
#   use composite_uniqueness for multi-column keys

check = Check(
    schema_name="public",
    table_name="users",
    column_name="email",
    detector_slug="uniqueness",
    params={},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / warn / fail
```

## Compatible with

- Great Expectations: `expect_column_values_to_be_unique`
- Soda: `duplicate_percent` (inverse)

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/uniqueness.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/uniqueness.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/uniqueness.py`

## When it works well

- Primary key or unique constraint columns where duplicate values are always a data quality issue.
- Works on any data type — string, numeric, timestamp.

## When it fails / Limitations

- Columns where duplicates are semantically expected (e.g. `customer_id` in a transactions table, `product_id` in an order-items table) — setting the threshold too tight produces constant false positives.
- Large tables: counting distinct values requires a full scan; consider sampling with caution as sampling underestimates duplicate rates.
- FPR at defaults (uniqueness_rate threshold): 0% (rule-based).
- Minimum recommended sample: 1 row.
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Primary key column | 1.0 | 1.0 | Exact uniqueness required |
| Near-unique (natural key) | 0.99 | 0.95 | Small tolerance for duplicates |
| Non-unique (FK column) | N/A | N/A | Not applicable; use cardinality_in_range |

## Failure modes and known limits

| Failure mode | Symptom | Fix |
|---|---|---|
| Natural duplicates | Some columns (category, status) legitimately have few unique values | Set `min_unique_fraction` based on expected cardinality |
| PK uniqueness vs value uniqueness | Primary key should be 100% unique; measure columns may have duplicates | Use separate checks for PK and measure columns |
