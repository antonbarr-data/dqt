# Stddev in range (`stddev_in_range`)

**Group:** `basic` · **Kind:** `aggregate` · **Version:** `1` · **Min N:** 2

## What it computes

Computes `STDDEV(col)` and returns 1.0 (fail) if outside `[min_val, max_val]`, otherwise 0.0. Catches variance collapse (constant feed) and variance explosion (corruption).

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `min_val` | `float` | `0.0` | Lower bound (inclusive) |
| `max_val` | `float` | `+inf` | Upper bound (inclusive) |

## Assumptions

- Bounds are calibrated from a historical stddev range, not from raw column range.
- Column has roughly stationary variance; heavy-tailed columns produce volatile stddev.
- Outliers are monitored separately (`mad_outlier_fraction`) so the stddev check fires for variance changes, not single outliers.

## When it works well

- Detecting variance collapse on a sensor or feed.
- Catching variance explosion from data corruption (INT overflow, NULL→0).

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Single outlier inflates stddev | One corrupt value pushes stddev above the upper bound | Pair with `mad_outlier_fraction`; investigate before widening bounds |
| Heavy-tailed distribution | Stddev is inherently unstable; check fires randomly | Use IQR (Q3 - Q1) as a robust spread measure via `sql_assertion_violation` |
| Near-constant column | A legitimate constant-value period fires the lower bound | Set `min_val=0` for columns that may temporarily be constant |
| Sample-size sensitivity | Stddev CI is proportional to `1/sqrt(N)`; small batches unreliable | Require N ≥ 30; use `quantile_in_range` at p25/p75 for small samples |

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

No statistical reference; rule-based bound check on the second moment.

Implementation: `packages/dqt/src/dqt/algorithms/basic/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="sensor_readings",
    column_name="temperature",
    detector_slug="stddev_in_range",
    params={'min_val': 0.1, 'max_val': 50.0},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Sensitive to outliers; second-moment statistics are not robust.
- Volatile on heavy-tailed columns even at large N.
