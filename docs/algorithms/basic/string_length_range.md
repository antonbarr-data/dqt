# String length range (`string_length_range`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

Evaluates `LENGTH(col::text) < min_len OR > max_len` per row and returns the violation fraction. Null values count as violations. Length is character length where the warehouse supports it.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `min_len` | `int` | `0` | Minimum acceptable character length (inclusive) |
| `max_len` | `int` | `255` | Maximum acceptable character length (inclusive) |

## Assumptions

- The column has a known length range (fixed-length identifier, format-bounded string).
- The warehouse's `LENGTH()` returns character length (not byte length) for multibyte data.
- Free-text columns with naturally variable length are not suitable for this check.

## When it works well

- Fixed-length identifiers (ISO-2, ISO-3, IBAN, SSN).
- Format-bounded strings (passport numbers, postal codes).

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Multibyte character length vs byte length | 3-character CJK string may be 9 bytes; LENGTH may return 9 | Use `CHAR_LENGTH()` if available; test on representative multibyte values |
| Null counted as violation | Null inflates the violation rate | Use `null_fraction` separately |
| Trailing spaces inflate length | 'USA   ' has length 6, not 3 | Trim at ingest or use `TRIM()` in `sql_assertion_violation` |
| Bounds too tight for edge-case valid values | A 2-char username is legitimate but `min_len=3` rejects it | Review real-world edge cases before setting bounds |

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

No statistical reference; deterministic length check.

Implementation: `packages/dqt/src/dqt/algorithms/basic/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="users",
    column_name="username",
    detector_slug="string_length_range",
    params={'min_len': 3, 'max_len': 32},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Character vs byte length behaviour is warehouse-dependent.
- Not appropriate for free-text or naturally variable-length columns.
