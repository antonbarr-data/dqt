# String case violation (`string_case_violation`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

For each non-null row checks `col = UPPER(col)`, `col = LOWER(col)`, or `col = INITCAP(col)`. Returns the fraction of non-null rows that violate the rule.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `case` | `str` | `"upper"` | `upper`, `lower`, or `title` |

## Assumptions

- The column has a strict casing convention (codes, enums, normalised identifiers).
- Free-text or proper-noun columns are excluded from this check.
- Warehouse collation handles UPPER/LOWER consistently with the source system.

## When it works well

- ISO country/currency codes (UPPER).
- Status/category enum values (lower).
- Display names with strict Title case requirements.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Legitimate mixed case | Product names, proper nouns, abbreviations ('iPhone', 'NASA') fail UPPER | Do not use on free-text or proper-noun columns |
| Source system changed casing | Upstream switched UPPER → lower; sudden spike in violations | Investigate upstream; standardise at ingest |
| Locale-dependent case mapping | UPPER('i') in Turkish locale produces 'I' (dotted I) | Set warehouse collation consistently |
| Title case with prepositions | INITCAP('de la Rosa') → 'De La Rosa' which fails | Use `sql_assertion_violation` with an exemption list |

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

No statistical reference; deterministic case check.

Implementation: `packages/dqt/src/dqt/algorithms/basic/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="countries",
    column_name="country_code",
    detector_slug="string_case_violation",
    params={'case': 'upper'},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Only checks case; does not normalise it.
- Locale-dependent behaviour requires warehouse collation alignment.
