# Grubbs' test (`grubbs`)

**Group:** `outliers_uni` · **Kind:** `sample` · **Version:** `1` · **Min N:** 3

## What it computes

Computes G = max|xi − x̄| / s and converts to a two-tailed p-value via the t-distribution with n - 2 degrees of freedom. Score = `1 - p_value`.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | Stateless detector — thresholds come from `STAT_SCALES` |

## Assumptions

- The column is approximately normal.
- At most one outlier is present (use `generalized_esd` for multiple).
- N is small to moderate (3 ≤ N ≤ ~100); test is over-sensitive at large N.

## When it works well

- Small-sample lab measurements, sensor readings, tight QA columns.
- Single-outlier detection with an interpretable p-value.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Non-normal data | FPR > 10% on lognormal; assumption violated | Use `mad_outlier_fraction` |
| Masking effect | Multiple outliers suppress each other's Z-scores | Use `generalized_esd` for multiple outliers |
| N < 7 | Test has no power; always returns no outlier | Collect more data |
| Large N (> 1000) | Over-sensitive; flags insignificant deviations | Use fraction-based detectors |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~5% | Calibrated at α=0.05 |
| Lognormal | ~20-40% | Assumes normality; very high FPR |
| Poisson | ~5-8% | Discrete; mild inflation |
| Beta | ~5% | Bounded |
| Pareto | ~30-50% | Heavy tail; do not use |
| Exponential | ~15-25% | Right-skew |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~5% |
| Lognormal | (default) | ~20-40% |
| Poisson | (default) | ~5-8% |
| Beta | (default) | ~5% |
| Pareto | (default) | ~30-50% |
| Exponential | (default) | ~15-25% |

## Citation

Grubbs, F.E. (1950). *Sample criteria for testing outlying observations*. Annals of Mathematical Statistics, 21(1), 27–58.

Implementation: `packages/dqt/src/dqt/algorithms/outliers_uni/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_gigs",
    column_name="price_usd",
    detector_slug="grubbs",
    params={},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Detects only the single most extreme value.
- Strong normality assumption.
