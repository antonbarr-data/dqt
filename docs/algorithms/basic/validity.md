# Validity (`validity`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

Pushes two aggregates to the warehouse: `SUM(CASE WHEN NOT (predicate) THEN 1 ELSE 0 END)` and `COUNT(*)`. Returns the validity rate (higher is better).

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `sql_predicate` | `str` | `"TRUE"` | SQL boolean expression that should be TRUE for valid rows |

## Assumptions

- Predicate is valid SQL in the target warehouse dialect.
- Null handling inside the predicate is explicit; `IN (...)` returns NULL for NULL inputs.
- Score direction is `higher_is_better` — alerting must read direction correctly.

## When it works well

- Allowed-value constraints on low-cardinality categorical columns.
- Schema-level type validations (`amount > 0`, `email LIKE '%@%'`).
- Replacing dbt `accepted_values` tests with continuous monitoring.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| NULL propagation | `status IN ('a','b')` returns NULL for NULL; nulls are not counted invalid by default | Add `status IS NOT NULL AND ...` if nulls should fail |
| Predicate too broad | `amount >= 0` misses the case where amount must be > 0 | Test against known-invalid rows before deploying |
| Predicate too strict | Fires on legitimate edge cases not in the allowed set | Enumerate all valid values; audit with the owning team |
| Score direction confusion | Score is `higher_is_better`; 0.90 means failure | Verify alerting reads `direction=higher_is_better` correctly |

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

Redman, T.C. (1996). *Data Quality for the Information Age*. Artech House. (Foundational validity dimension.)

Implementation: `packages/dqt/src/dqt/algorithms/basic/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="bookings",
    column_name="status",
    detector_slug="validity",
    params={'sql_predicate': "status IN ('pending','active','completed','cancelled')"},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Inherits SQL-correctness risks; tests well before deploying.
- Direction is `higher_is_better` — alerting must be wired accordingly.
