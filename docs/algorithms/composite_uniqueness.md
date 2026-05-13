# `basic.composite_uniqueness`

> *Composite key uniqueness* — fraction of rows that are duplicates on a multi-column key.

## What it checks

Concatenates the specified key columns into a single composite key string (null-safe), counts total rows versus distinct composite values, and returns the duplicate fraction `(total - distinct) / total`. A score of 0.0 means all composite key values are unique; 1.0 means every row is a duplicate.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `key_columns` | `list[str]` | *(required)* | List of column names that together form the composite key |

## Scale (STAT_SCALES)

| Threshold | Value |
|---|---|
| warn | 0.001 (0.1% duplicate rows) |
| fail | 0.01 (1% duplicate rows) |
| direction | lower_is_better |

## Example

```python
from dqt import Check, Runner, MemoryStore
from dqt.algorithms.basic.column_pairs import CompositeUniquenessDetector

# CompositeUniquenessDetector(
#     key_columns=["col_a", "col_b"],  # columns that together form the unique key;
#                                       # list the most selective column first for readability;
#                                       # at least 2 columns required
# )

check = Check(
    schema_name="public",
    table_name="order_items",
    detector_slug="composite_uniqueness",
    params={"key_columns": ["order_id", "product_id"]},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / warn / fail
```

## Compatible with

- Great Expectations: `expect_compound_columns_to_be_unique`
- Soda: `duplicate_count` (on multi-column group)

## Implementation

[`packages/dqt/src/dqt/algorithms/basic/column_pairs.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/basic/column_pairs.py)

## Source

`packages/dqt/src/dqt/algorithms/basic/column_pairs.py`

## When it works well

- Composite primary keys or natural composite unique constraints (e.g. `(order_id, line_item_id)`, `(user_id, date)`) where the combination must be unique.
- Complements `uniqueness` for multi-column keys.

## When it fails / Limitations

- Partial key columns that are individually non-unique — the check is only meaningful for the combination; individual-column uniqueness should use `uniqueness`.
- Very large tables: the COUNT(DISTINCT) aggregation over multiple columns is expensive; ensure indexes cover the key columns.
- FPR at defaults: 0% (rule-based).
- Minimum recommended sample: 1 row.
- FPR at defaults on clean normal data: 0%.
- FPR at defaults on heavy-tailed data: 0% (rule-based).

## Recommended thresholds by data shape

| Data shape | warn | fail | Notes |
|---|---|---|---|
| Composite primary key | 1.0 | 1.0 | Exact uniqueness required |
| Near-unique composite | 0.99 | 0.95 | Small tolerance |
| Non-unique combination | N/A | N/A | Not applicable |

## Failure modes and known limits

`composite_uniqueness` is a deterministic rule: FPR is 0% for truly unique composite keys. False positives come from over-strict key definitions or from sampling effects on very large tables. False negatives (missed duplicates) come from sampling - a reservoir sample of 100k rows may not catch rare duplicates.

| Failure mode | Symptom | Fix |
|---|---|---|
| Sampling misses rare duplicates | Duplicate fraction in sample is 0% but duplicates exist at full-table scale | Run the check against the full table for critical keys; increase sample size via `sample_size` param |
| Null in key column | NULL values are treated as distinct by most warehouses - two rows with NULL in a key column count as unique | Use `null_fraction` on each key column first; treat any null in a key column as a violation |
| Partial key definition (missing a column) | A key that omits a discriminating column produces false duplicate alerts on legitimately distinct rows | Verify the key definition covers all natural-key columns |
| Late-arriving duplicates deduplicated upstream | A pipeline that deduplicates on load means no duplicates at check time, but the deduplication itself may be lossy | Add checks both upstream (before dedup) and downstream (after dedup) |
| Reprocessed / incremental loads create temporary duplicates | Duplicate fraction spikes during a reload then drops to zero | Schedule the check after the full load completes; exclude the reload window |

### FPR table

| Scenario | Expected FPR | Notes |
|---|---|---|
| Stable table with true PK | 0% | Rule-based; no statistical approximation |
| Incremental append table | 0% at steady state | May fire during reload windows |
| Sample of large table | Near 0% | Very rare duplicates may be missed entirely |

### Threshold recommendations

- For composite primary keys: set warn=fail=0 (any duplicate is an immediate failure).
- For near-unique combinations (e.g. `(user_id, date)` where some users have multiple records per day by design): set warn=0.001 / fail=0.01 to allow a small expected rate.
- Do not loosen thresholds to suppress fires during reloads; instead exclude reload windows using check scheduling.
