# `referential.referential_integrity_rate`

> *Referential integrity* — fraction of FK values that exist in the parent table.

## What it checks

For each non-null FK value in the child column, checks whether it exists in `parent_table.parent_col` using a `NOT IN (SELECT ...)` subquery. Returns `1 - (orphan_count / total_count)`. A score of 1.0 means perfect referential integrity; lower scores indicate orphan rows. Because the subquery scans the parent table on every run, use this on reasonably-sized parent tables only or pair with a cost guard.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `parent_table` | `str` | *(required)* | Fully qualified parent table name (e.g. `public.customers`) |
| `parent_col` | `str` | `"id"` | Primary key column in the parent table |

## Scale (STAT_SCALES)

| Threshold | Value |
|---|---|
| warn | 0.99 (below 99% integrity) |
| fail | 0.95 (below 95% integrity) |
| direction | higher_is_better |

## Example

```python
from dqt import Check, Runner, MemoryStore
from dqt.algorithms.referential.referential import ReferentialIntegrityDetector

det = ReferentialIntegrityDetector(
    parent_table="public.customers",  # fully-qualified table name of the parent
                                      # (e.g. "public.fct_gigs").
    parent_col="id",                  # the primary key column in the parent table
                                      # (default "id").
    # score = orphan fraction (fraction of child rows with no matching parent key).
    # 0.0 = perfect integrity.
)

check = Check(
    schema_name="public",
    table_name="orders",
    column_name="customer_id",
    detector_slug="referential_integrity_rate",
    params={"parent_table": "public.customers", "parent_col": "id"},
)
# result = Runner(MemoryStore()).run(check, adapter)
# print(result.verdict)   # pass / warn / fail
```

## Compatible with

- Great Expectations: `expect_column_values_to_be_in_set` (with parent lookup)
- Soda: `referential_integrity` (enterprise)

## Implementation

[`packages/dqt/src/dqt/algorithms/referential/referential.py`](https://github.com/antonbarr-data/dqt/blob/main/packages/dqt/src/dqt/algorithms/referential/referential.py)

## Source

`packages/dqt/src/dqt/algorithms/referential/referential.py`
