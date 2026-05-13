# Cardinality in range (`cardinality_in_range`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

Computes `COUNT(DISTINCT col)` and returns 1.0 (fail) if the distinct count is outside `[min_val, max_val]`, otherwise 0.0. No baseline is fitted; bounds are declared on the Check. Useful for enum-like columns with stable cardinality and for catching dimension-table runaway.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `min_val` | `int` | `1` | Lower bound (inclusive) on COUNT(DISTINCT col) |
| `max_val` | `int` | `2**31` | Upper bound (inclusive) on COUNT(DISTINCT col) |

## Assumptions

- The column has a meaningful notion of distinct value count (categoricals, low-cardinality IDs).
- The acceptable cardinality is known up front and stable between schema changes.
- NULL handling matches the warehouse's `COUNT(DISTINCT)` semantics (most warehouses ignore NULL).

## When it works well

- Stable enums and status columns with a fixed valid set.
- Detecting cardinality explosions (a date column suddenly behaving like a timestamp).
- Cardinality collapses (a category disappearing after a bad ETL run).

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| New legitimate category introduced | Upper-bound fires the moment a new enum member appears | Widen bounds on business-level category changes; pair with `set_membership` to monitor allowed values |
| Sample-size dependency on high-cardinality columns | 100 k sample of a 50 M-row ID table shows lower distinct count than full table | Set bounds relative to sample size, not table size, or run the check against the full table |
| Alias / typo drift ("USA" vs "US") | Cardinality appears correct while data is semantically inconsistent | Pair with `set_membership` or `regex_match` to enforce canonical values |
| NULL counted as a distinct value | Some warehouses count NULL as one distinct value, others do not | Verify warehouse behaviour; track `null_fraction` separately |

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
    table_name="orders",
    column_name="status",
    detector_slug="cardinality_in_range",
    params={'min_val': 3, 'max_val': 6},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Deterministic — FPR is 0% for clean data with correct bounds.
- Threshold drift if business categories evolve; review quarterly.
- Does not detect aliasing inside an otherwise correct cardinality.
