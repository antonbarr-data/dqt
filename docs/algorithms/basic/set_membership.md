# Set membership (`set_membership`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

Evaluates `col NOT IN (allowed_values)` per row and returns the violation fraction. 0.0 means all values are members of the allowed set.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `allowed_values` | `list | set` | `(required, non-empty)` | Complete set of permitted values |

## Assumptions

- The allowed set is exhaustive and updated whenever the business introduces new categories.
- Case and whitespace variants are normalised upstream or explicitly enumerated.
- NULL is treated as a violation (not a member of any set); use `null_fraction` if a separate handling is desired.

## When it works well

- Enum / status columns with a known fixed allowed-values set.
- ISO codes (country, currency) with a stable membership set.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Allowed set expansion | New valid categories appear and fire as violations | Refresh the allowed list when business adds new categories |
| Case sensitivity | 'Active' vs 'active' treated as different values | Normalise upstream or set `case_sensitive=False` |
| Whitespace variants | 'paid ' is not in the set | Trim upstream or in a `sql_assertion_violation` |
| Free-text column | Maintaining an exhaustive allowed set is infeasible | Use `regex_match` or a semantic check instead |

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
    detector_slug="set_membership",
    params={'allowed_values': ['pending', 'paid', 'shipped', 'cancelled']},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Maintenance overhead: allowed list must evolve with the business.
- Not suitable for high-cardinality columns.
