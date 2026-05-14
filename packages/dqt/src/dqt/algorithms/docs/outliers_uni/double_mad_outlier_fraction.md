# Double MAD (`double_mad_outlier_fraction`)

**Group:** `outliers_uni` · **Kind:** `sample` · **Version:** `1` · **Min N:** 20

## What it computes

Computes separate MAD_left (for values ≤ median) and MAD_right (for values ≥ median). Each value's modified Z-score uses the side-appropriate MAD. Returns the fraction exceeding `threshold`.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `threshold` | `float` | `6.5` | Modified Z-score cutoff; 3.5 for near-Gaussian, 6.5 for lognormal/revenue |

## Assumptions

- Numeric column with asymmetric / skewed distribution.
- Sample size ≥ 20 with at least ~10 values on each side of the median.
- Default threshold 6.5 calibrated for lognormal(0,1); use 3.5 for near-Gaussian data.

## When it works well

- Right-skewed columns (transaction amounts, latencies, file sizes).
- Heavy-skew cases where adjusted boxplot exponential correction becomes unstable.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Symmetric data | Double-MAD does no harm but adds no benefit over MAD | Use `mad_outlier_fraction` for simplicity |
| Very small reference (N < 50) | Per-side half-MADs noisy below 25 points each | Increase baseline window |
| Bimodal distributions | One side's MAD may span both modes; threshold misleading | Use `isolation_forest_fraction` or segment |
| MAD = 0 on one side | Many duplicates at the boundary; epsilon fallback used | Investigate the boundary cluster |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~0.0% | Threshold 6.5 very conservative for Gaussian |
| Lognormal | ~1.0% | Calibrated target shape |
| Poisson | ~0.0% | Discrete; threshold conservative |
| Beta | ~0.0% | Bounded |
| Pareto | ~3% | Heavy tail; small tail mass exceeds threshold |
| Exponential | ~0.05% | Right-skew handled by side-specific MAD |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~0.0% |
| Lognormal | (default) | ~1.0% |
| Poisson | (default) | ~0.0% |
| Beta | (default) | ~0.0% |
| Pareto | (default) | ~3% |
| Exponential | (default) | ~0.05% |

## Citation

Rousseeuw, P.J. & Croux, C. (1993). *Alternatives to the Median Absolute Deviation*. JASA, 88(424), 1273–1283.

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
    detector_slug="double_mad_outlier_fraction",
    params={'threshold': 3.5},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Per-side MAD requires balanced data around the median.
- Threshold must be calibrated to the data shape (lognormal vs Gaussian).
