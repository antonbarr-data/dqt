# Outlier-fraction drift (`outlier_fraction_drift`)

**Group:** `outliers_uni` · **Kind:** `sample` · **Version:** `1` · **Min N:** 3

## What it computes

Meta-detector that operates on a time series of historical outlier fractions (one column named `outlier_fraction`). Fits a tolerance range (IQR, percentile, or z-score) and computes the normalised deviation of the current period's outlier fraction outside the range.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `method` | `str` | `"iqr"` | Range estimation: `iqr`, `percentile`, or `zscore` |
| `k` | `float` | `1.5` | IQR multiplier (for `iqr`) or z-threshold (for `zscore`) |
| `lower_pct` | `float` | `5.0` | Lower percentile (for `percentile` method) |
| `upper_pct` | `float` | `95.0` | Upper percentile (for `percentile` method) |

## Assumptions

- Input is a single-column DataFrame `outlier_fraction` with at least 3 historical points.
- The upstream outlier detector that produced the fractions is calibrated.
- Variance of the outlier fraction is moderate over the reference period.

## When it works well

- Meta-monitoring on long-running outlier-rate KPIs.
- Catching slow-burn degradation that single-window outlier thresholds miss.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Volatile fraction time series | Wide IQR range masks real anomalies | Use `method='percentile'` with narrow bounds or `adwin` |
| Tiny historical window (< 3 points) | Cannot fit a range | Collect more history before enabling |
| Seasonal outlier rate | Range may be wide; legitimate seasonal peaks fire | Fit per-season; or use a STL-based approach |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~5% | IQR-style tolerance band on the fraction series |
| Lognormal | ~10-15% | Underlying outlier rate is noisier |
| Poisson | ~6% | Discrete; mild inflation |
| Beta | ~5% | Bounded |
| Pareto | ~12-18% | Heavy tail; underlying detector FPR elevated |
| Exponential | ~7-10% | Right-skew |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~5% |
| Lognormal | (default) | ~10-15% |
| Poisson | (default) | ~6% |
| Beta | (default) | ~5% |
| Pareto | (default) | ~12-18% |
| Exponential | (default) | ~7-10% |

## Citation

Tukey, J.W. (1977). *Exploratory Data Analysis*. Addison-Wesley. (IQR fences as the canonical univariate range method.)

Implementation: `packages/dqt/src/dqt/algorithms/outliers_uni/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_gigs_outlier_history",
    column_name="outlier_fraction",
    detector_slug="outlier_fraction_drift",
    params={},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Requires a pre-computed history of outlier fractions.
- Interpretation only as good as the upstream outlier detector.
