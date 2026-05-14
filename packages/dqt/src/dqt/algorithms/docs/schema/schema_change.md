# Schema change (`schema_change`)

**Group:** `schema` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

On `fit()`, records the current `{column_name: data_type}` mapping from `describe_columns()`. On each run compares the current schema to baseline; returns 0.0 if identical, 1.0 with a breakdown of added/removed/type-changed columns otherwise.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | Stateless detector — thresholds come from `STAT_SCALES` |

## Assumptions

- The baseline schema was captured against the same warehouse engine.
- Type-string canonicalisation matches between baseline and current (e.g. `int64` vs `int`).
- Column ordering is not the primary criterion (most warehouses do not preserve order).

## When it works well

- Detecting accidental upstream schema changes (drops, renames, type promotions).
- Catching column renames as remove + add events that would otherwise be silent.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Column renames fire as remove+add | Two events for what is logically one rename | Pair with fuzzy-matching schema diff (task J.14) |
| Implicit casting (INT → BIGINT) | Type-string difference fires even though semantics unchanged | Normalise type strings before comparison |
| Additive-only evolution | Adding a nullable column is sometimes acceptable | Use `allow_new_columns=True` if team frequently adds columns |

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

No statistical reference; deterministic schema-diff check.

Implementation: `packages/dqt/src/dqt/algorithms/schema/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_orders",
    detector_slug="schema_change",
    params={},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Doesn't detect semantic changes (column meaning) where name and type are stable.
- Both warn and fail thresholds are 0.5 — any change is an immediate fail.
