# Z-score outlier (`zscore_outlier_fraction`)

**Group:** `outliers_uni` · **Kind:** `sample` · **Version:** `1` · **Min N:** 30

## What it computes

Records reference mean and stddev. Returns the fraction of current values whose absolute Z-score `|xi - μ| / σ` exceeds `threshold` (default 3.0).

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `threshold` | `float` | `3.0` | Z-score cutoff; 3.0 = three-sigma (~0.27% on Gaussian) |

## Assumptions

- Reference is approximately Gaussian (verified via classifier when auto-selected).
- Sample size ≥ 30 for central-limit stabilisation of mean/std.
- Reference is not contaminated by outliers (Z-score has 0% breakdown point).

## When it works well

- Confirmed near-normal columns (counts, bounded ratios, z-standardised scores).
- Auto-selected by `auto_outlier` for normal distributions.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Heavy-tailed data (revenue, latency) | Z-score inflated by extreme values in mean/std; FPR ~100% at default threshold | Use `mad_outlier_fraction` or `double_mad_outlier_fraction` |
| Non-stationary reference (trending data) | FPR doubles per unit of trend slope | Detrend before scoring; or use `stl_residual_zscore` |
| Small reference (N < 30) | Mean/std noisy; scores unstable | Collect more reference data |
| All-identical reference | std=0 → ZeroDivision; masked to 1e-10 | Add `uniqueness` check upstream |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~0.3% | Theoretical 0.27% at three-sigma threshold |
| Lognormal | ~5-15% | Do not use raw Z-score on skewed data |
| Poisson | ~1% | Approximately normal at large λ |
| Beta | ~1% | Bounded; close to normal |
| Pareto | ~10-20% | Heavy tail; FPR very inflated |
| Exponential | ~3-8% | Right-skew |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~0.3% |
| Lognormal | (default) | ~5-15% |
| Poisson | (default) | ~1% |
| Beta | (default) | ~1% |
| Pareto | (default) | ~10-20% |
| Exponential | (default) | ~3-8% |

## Citation

Press, W.H. et al. (1992). *Numerical Recipes in C* (2nd ed.), §14.1. Cambridge University Press. (Standard Z-score derivation.)

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
    detector_slug="zscore_outlier_fraction",
    params={'threshold': 3.0},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Only valid on confirmed Gaussian data.
- 0% breakdown point — single outlier in reference inflates both moments.
