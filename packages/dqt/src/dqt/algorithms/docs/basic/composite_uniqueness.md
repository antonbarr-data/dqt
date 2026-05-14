# Composite uniqueness (`composite_uniqueness`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

Builds a null-safe composite key from `key_columns`, computes the duplicate fraction `(total - distinct) / total`, and returns it. 0.0 means the composite key is unique.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `key_columns` | `list[str]` | `(required)` | Columns that together form the composite unique key (≥2) |

## Assumptions

- The supplied `key_columns` jointly form the natural unique key.
- Null values within any key column are folded into a sentinel for the composite (handled by the SQL); two NULL-key rows are treated as the same composite if your warehouse so treats them.
- Sample-based runs may miss rare duplicates; for hard PK enforcement run against the full table.

## When it works well

- Composite primary keys like `(order_id, line_item_id)` or `(user_id, date)`.
- Catching duplicate inserts after late-arriving or reprocessed loads.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Sampling misses rare duplicates | Sample-level duplicate fraction is 0% but duplicates exist at full-table scale | Run against the full table for critical keys; raise `sample_size` |
| NULL in a key column | Two rows with NULL in a key column may count as distinct depending on warehouse | Use `null_fraction` on each key column; treat any null in a key column as a violation |
| Partial key definition (missing a column) | Real distinct rows fire as duplicates because the discriminating column was omitted | Verify the composite key covers all natural-key columns |

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

No statistical reference; rule-based check.

Implementation: `packages/dqt/src/dqt/algorithms/basic/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="order_items",
    detector_slug="composite_uniqueness",
    params={'key_columns': ['order_id', 'product_id']},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Deterministic on a full-table scan; sample-based runs have non-zero false-negative rate.
- Cannot detect duplicates that are deduplicated upstream before the check runs.
