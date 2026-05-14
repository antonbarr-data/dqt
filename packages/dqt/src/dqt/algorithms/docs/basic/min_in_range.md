# Min in range (`min_in_range`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

Computes `MIN(col)` and returns 1.0 (fail) if outside `[min_val, max_val]`, otherwise 0.0. Catches negative or zero values in strictly-positive columns.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `min_val` | `float` | `0.0` | Lower bound (inclusive) |
| `max_val` | `float` | `+inf` | Upper bound (inclusive) |

## Assumptions

- A hard physical or business floor exists for the column.
- Single-value extreme low values are operationally relevant.

## When it works well

- Strictly positive columns (price, quantity, duration_ms).
- Domain-bounded columns (rating ≥ 1, age ≥ 0).

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Single refund or credit creates a negative value | One legitimate credit note fires the check | Set `min_val` to the minimum allowed credit; or filter credits upstream |
| Sample-size dependence | As N grows the minimum decreases even on stable distributions | Use `quantile_in_range` at p0.01 |
| Zero-value records from a default fill | An ETL default-fill produces zeros | Detect at the ETL layer or set `min_val=0` and accept zeros |
| Sentinel values from upstream (e.g. `-1` = unknown) | Sentinel fires the check legitimately | Filter upstream or use `sql_assertion_violation` with explicit sentinel handling |

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

No statistical reference; rule-based bound check.

Implementation: `packages/dqt/src/dqt/algorithms/basic/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="orders",
    column_name="amount",
    detector_slug="min_in_range",
    params={'min_val': 0.0, 'max_val': 1000000.0},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Minimum is the most variable order statistic; unstable on small samples.
- Not appropriate for columns without a domain floor.
