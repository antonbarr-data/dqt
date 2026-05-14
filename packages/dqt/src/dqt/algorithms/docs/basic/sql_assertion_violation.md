# SQL assertion violation (`sql_assertion_violation`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

Evaluates `NOT (condition)` per row and returns the fraction of violations. The `condition` is a trusted SQL boolean expression that has access to all columns in the table.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `condition` | `str` | `(required)` | SQL boolean expression that must be TRUE for every valid row |

## Assumptions

- The condition is valid SQL in the target warehouse dialect.
- Null handling inside the predicate is explicit (`amount IS NOT NULL AND amount > 0`).
- The condition has been tested against representative warehouse data before deployment.

## When it works well

- Cross-column business rules that don't fit any single-column check.
- Statistical assertions (e.g. comparing to a STDDEV).
- Compliance checks requiring custom SQL.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| NULL propagation | `amount > 0` returns NULL (not FALSE) for NULL rows; nulls are not counted as violations | Use `amount IS NOT NULL AND amount > 0`; or test nulls separately |
| SQL dialect incompatibility | Postgres-specific function fails on Snowflake | Write standard SQL or test on every target engine |
| Full-table scan in condition | Subquery causes a full-table scan every run | Pre-aggregate to a summary table; use `referential_integrity_rate` for FK checks |
| Division by zero | `amount / quantity` fails when `quantity = 0` | Use `NULLIF(quantity, 0)` to avoid division by zero |
| Condition weakened to suppress alerts | Condition loosened during an incident; root cause not fixed | Track condition changes in the audit log; require HITL approval |

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

No statistical reference; user-supplied predicate.

Implementation: `packages/dqt/src/dqt/algorithms/basic/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_bookings",
    detector_slug="sql_assertion_violation",
    params={'condition': 'amount_paid_usd > 0 AND status IS NOT NULL AND buyer_id IS NOT NULL'},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- FPR is entirely user-controlled by the SQL correctness.
- Not portable across warehouse dialects without testing.
- Performance depends entirely on the SQL complexity.
