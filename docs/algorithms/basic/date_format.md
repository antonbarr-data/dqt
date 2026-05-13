# Date format (`date_format`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

Converts the declared format string to a structural regex and counts non-null rows whose string representation does not match. Validates *shape* of the date string (digit counts, separators), not calendar validity.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `date_format` | `str` | `"%Y-%m-%d"` | Format string using strptime tokens or SQL tokens |

## Assumptions

- All non-null values in the column should match a single declared format.
- Format tokens use Python strptime (`%Y`, `%m`) or SQL (`YYYY`, `MM`) — both supported.
- The cast-to-text representation in the target warehouse is stable for date/timestamp columns.

## When it works well

- Strict ISO 8601 columns where any deviation is a real ingest bug.
- Date keys and partition columns where downstream consumers parse on shape.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Mixed format source systems | Minority format fires as a violation (e.g. 5% of rows use MM/DD/YYYY) | Standardise at ingest; for mixed-format columns use `sql_assertion_violation` with CASE WHEN |
| Timezone suffix not in pattern | `2024-01-15T10:30:00Z` fails `%Y-%m-%dT%H:%M:%S` due to trailing `Z` | Include the suffix in the pattern or strip it upstream |
| Single-digit month/day padding | `2024-1-5` fails `%Y-%m-%d` (expects zero-padding) | Normalise to zero-padded form upstream |
| Date-typed column under cast | Cast-to-text format varies by warehouse | Test the cast output format in your warehouse before setting the pattern |

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

No statistical reference; structural pattern check.

Implementation: `packages/dqt/src/dqt/algorithms/basic/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="events",
    column_name="event_date",
    detector_slug="date_format",
    params={'date_format': '%Y-%m-%d'},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Validates string shape, not calendar validity (`2024-02-30` passes).
- Locale-dependent format separators must be encoded in the pattern.
- FPR is binary: 0% if the pattern matches the data exactly, otherwise close to 100% for the non-matching format.
