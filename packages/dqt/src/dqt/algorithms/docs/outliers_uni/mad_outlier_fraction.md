# MAD outlier (`mad_outlier_fraction`)

**Group:** `outliers_uni` · **Kind:** `sample` · **Version:** `1` · **Min N:** 10

## What it computes

Computes modified Z-score `|xi − median| × 0.6745 / MAD`. Records median and MAD from the reference. Returns the fraction of current values whose modified Z-score exceeds `threshold`.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `threshold` | `float` | `11.0` | Modified Z-score cutoff; 3.5 for near-Gaussian, 11.0 for lognormal/revenue |

## Assumptions

- Numeric column with unimodal, roughly symmetric (or symmetric-after-transform) distribution.
- Sample size ≥ 10 for stable MAD estimate.
- Default threshold 11.0 calibrated for lognormal; use 3.5 for near-Gaussian data.

## When it works well

- Heavy-tailed columns where Z-score over-flags.
- Contaminated reference data — MAD has 50% breakdown point.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Normal data with default threshold 11.0 | Very few outliers flagged even when 5% are genuine | Use `suggest_threshold()` or set `threshold=3.5` |
| Zero MAD (all-identical reference) | Division-by-zero masked; Z-scores become absolute deviations | Add `completeness` and uniqueness checks upstream |
| Bimodal reference distribution | MAD captures inter-mode gap as variance; outlier fraction inflated | Use `isolation_forest_fraction` or segment data |
| Very small reference (N < 30) | Median estimate noisy; threshold effectively random | Increase baseline window |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~0.0% | Threshold 11.0 very conservative for Gaussian |
| Lognormal | ~1.1% | Calibrated target shape |
| Poisson | ~0.0% | Discrete; conservative |
| Beta | ~0.0% | Bounded |
| Pareto | ~3-4% | Heavy tail |
| Exponential | ~0.02% | Right-skew handled by MAD |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~0.0% |
| Lognormal | (default) | ~1.1% |
| Poisson | (default) | ~0.0% |
| Beta | (default) | ~0.0% |
| Pareto | (default) | ~3-4% |
| Exponential | (default) | ~0.02% |

## Citation

Leys, C. et al. (2013). *Detecting outliers: Do not use standard deviation around the mean, use absolute deviation around the median*. Journal of Experimental Social Psychology, 49(4), 764–766.

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
    detector_slug="mad_outlier_fraction",
    params={'threshold': 3.5},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Threshold must match the data shape (Gaussian vs heavy-tailed).
- Symmetric MAD; for asymmetric data use `double_mad_outlier_fraction`.
