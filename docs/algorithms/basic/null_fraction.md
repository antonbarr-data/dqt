# Null fraction (`null_fraction`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

Counts NULL values in the column and divides by total row count. 0.0 means no nulls, 1.0 means the column is fully null. Stateless — thresholds come from STAT_SCALES.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | Stateless detector — thresholds come from `STAT_SCALES` |

## Assumptions

- NULL is the canonical missing-value marker; placeholder strings like 'N/A' are not detected.
- The default thresholds (warn 1%, fail 5%) match a strict expectation; structural-null columns need per-check thresholds.

## When it works well

- Required-field columns where any null is operationally significant.
- Tracking null-rate regressions over time on critical IDs and keys.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Structural nulls (nullable FK, optional attribute) | Constantly fires at the 1% default | Set per-check `null_fraction` to baseline_null_fraction × 1.5 |
| Placeholder strings instead of NULL | Null rate appears 0% while semantic missingness is high | Pair with `validity` / `regex_match` to catch placeholders |
| JOIN-induced nulls | Null fraction spikes after a failed LEFT JOIN — lineage signal, not data quality | Investigate lineage upstream; pair with `schema_change` |

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
    column_name="customer_id",
    detector_slug="null_fraction",
    params={},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Detects NULL only — placeholder strings and sentinels need additional checks.
- Defaults are conservative; calibrate per column for known structural-null columns.
