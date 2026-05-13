# Set exclusion (`set_exclusion`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

Evaluates `col IN (forbidden_values)` per row and returns the violation fraction. 0.0 means no values match the forbidden set.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `forbidden_values` | `list | set` | `(required, non-empty)` | Values that must not appear in the column |

## Assumptions

- The forbidden set is maintained and reviewed when new bad values emerge.
- Case and whitespace variants are explicitly enumerated or normalised upstream.
- NULL is not silently treated as a match — handle nulls in a separate check.

## When it works well

- Blocklists of sentinel values (`'N/A'`, `'test'`, `'DELETE'`).
- Deprecated enum members that must not reappear.
- PII compliance: known-bad email accounts, sandbox IDs.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Stale blocklist | New sentinel values (e.g. 'UNKNOWN') enter the table and pass the check | Audit distinct values quarterly; trigger re-review when `cardinality_in_range` detects new categories |
| Case sensitivity mismatch | 'test' is forbidden but 'TEST' passes | Add all case variants or normalise case upstream |
| Whitespace variants | 'banned ' (trailing space) is not caught by 'banned' | Trim upstream or use `TRIM()` in `sql_assertion_violation` |
| Null is forbidden but passes | NULL is not matched by `IN (...)` in SQL | Use `null_fraction` for nulls |

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
    table_name="users",
    column_name="email",
    detector_slug="set_exclusion",
    params={'forbidden_values': ['test@example.com', 'noreply@example.com']},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Maintenance overhead: blocklist must be reviewed as bad values evolve.
- Performance degrades on `IN` lists > 1000 values; switch to a blocklist table.
