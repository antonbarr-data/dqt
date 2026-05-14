# Referential integrity rate (`referential_integrity_rate`)

**Group:** `referential` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

For each non-null FK value in the child column, checks existence in `parent_table.parent_col` via `NOT IN (SELECT ...)`. Returns `1 - (orphan_count / total_count)`.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `parent_table` | `str` | `(required)` | Fully-qualified parent table name |
| `parent_col` | `str` | `"id"` | Primary key column in the parent table |

## Assumptions

- Parent table is reasonably sized (subquery scans it on every run).
- FK column reflects a real referential relationship.
- Soft deletes in the parent table are handled upstream.

## When it works well

- FK-like relationships across tables in the warehouse.
- Detecting orphans caused by ETL ordering issues or parent-table deletions.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Soft deletes vs hard deletes | References to soft-deleted rows are not real integrity violations | Filter soft-deleted rows before computing the rate |
| Cross-schema references | Some warehouses do not support cross-schema FK queries via info_schema | Specify the parent table fully-qualified |
| Performance on large parent tables | Subquery scan is expensive on every run | Ensure indexes on the join columns; or materialise a parent-key summary |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | 0% | Deterministic rule; bounds determine FPR exactly |
| Lognormal | 0% | Deterministic rule |
| Poisson | 0% | Deterministic rule |
| Beta | 0% | Deterministic rule |
| Pareto | 0% | Deterministic rule |
| Exponential | 0% | Deterministic rule |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | 0% |
| Lognormal | (default) | 0% |
| Poisson | (default) | 0% |
| Beta | (default) | 0% |
| Pareto | (default) | 0% |
| Exponential | (default) | 0% |

## Citation

No statistical reference; rule-based referential check.

Implementation: `packages/dqt/src/dqt/algorithms/referential/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="orders",
    column_name="customer_id",
    detector_slug="referential_integrity_rate",
    params={'parent_table': 'public.customers', 'parent_col': 'id'},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Subquery cost scales with parent-table size.
- Score is `higher_is_better`; alerting must read direction correctly.
