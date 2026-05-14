# Completeness (`completeness`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 1

## What it computes

Computes `1 - (null_count / total_count)`. 1.0 means every value is present, 0.0 means the column is fully null. Inverse of `null_fraction` with a `higher_is_better` direction.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | Stateless detector — thresholds come from `STAT_SCALES` |

## Assumptions

- NULL is the canonical missing-value marker; empty strings and sentinels like 'N/A' are not detected unless explicitly mapped.
- Per-column completeness expectations are configured via STAT_SCALES (warn=0.95, fail=0.90) or overridden per check.

## When it works well

- Required-field SLAs (every order has a customer_id).
- Tracking completeness regressions over time for any nullable column.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Structural nulls (optional columns) | A column that is naturally 30% null fails default thresholds | Set per-check `min_completeness`; or use `null_fraction` with a calibrated baseline |
| Placeholder strings ("N/A", "unknown") | Completeness reports 1.0 because the placeholder is non-null | Pair with `validity` or `regex_match` to catch semantic incompleteness |
| Table truncation | Total row count drops; completeness on remaining rows still passes | Pair with `row_count_in_range` or `volume` |

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
    column_name="email",
    detector_slug="completeness",
    params={},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Detects NULL only; does not detect semantic missingness.
- Score is `higher_is_better` — be careful with downstream alerting wired for `lower_is_better`.
