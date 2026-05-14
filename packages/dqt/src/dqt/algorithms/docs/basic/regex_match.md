# Regex match (`regex_match`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

Evaluates `col::text !~ pattern` (Postgres POSIX) on each row and returns the violation fraction. NULLs count as violations.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `pattern` | `str` | `".*"` | POSIX regex that valid values must match |

## Assumptions

- The pattern is anchored with `^` and `$` for full-string matching (otherwise partial matches mask invalid prefixes/suffixes).
- The target warehouse supports POSIX ERE; Python-only syntax is not portable.
- Case-sensitivity matches the business rule.

## When it works well

- Strict format columns (emails, phone numbers, UUIDs, ISO codes).
- Compliance / PII pattern detection.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Pattern too strict for international data | International phone numbers / names fail the pattern | Test against a representative international sample |
| Null counted as violation | Nulls inflate the violation rate | Use `null_fraction` separately; set `null_handling=exclude` |
| Regex catastrophic backtracking | Complex pattern on wide text column times out | Avoid nested quantifiers; test with `EXPLAIN` |
| Warehouse POSIX vs Python regex dialect | Pattern uses Python-only syntax | Use only POSIX ERE; test against your warehouse |

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

No statistical reference; pattern-match check.

Implementation: `packages/dqt/src/dqt/algorithms/basic/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="users",
    column_name="phone",
    detector_slug="regex_match",
    params={'pattern': '^\\+?[0-9\\-\\s]{7,15}$'},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Locale and collation affect case-insensitive matching; verify per warehouse.
- Multibyte / Unicode characters may behave unexpectedly without explicit collation.
