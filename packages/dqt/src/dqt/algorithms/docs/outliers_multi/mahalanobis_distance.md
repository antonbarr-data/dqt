# Mahalanobis distance (`mahalanobis_distance`)

**Group:** `outliers_multi` · **Kind:** `sample` · **Version:** `1` · **Min N:** 100

## What it computes

Records mean vector μ and inverse covariance Σ⁻¹ from numeric columns of the reference. Computes squared Mahalanobis distance for each current row and counts the fraction beyond the χ² critical value at `p_threshold`.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `p_threshold` | `float` | `0.001` | Chi-square tail probability defining the outlier boundary |

## Assumptions

- Reference is approximately multivariate normal.
- Number of rows ≥ 5 × n_features for stable covariance.
- Features are not perfectly collinear (covariance regularised by adding εI).

## When it works well

- Moderate-dimensional (2–20) features with correlated Gaussian-like structure.
- Detecting joint anomalies that individual-column checks would miss.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Singular covariance matrix | Collinear features → singular covariance; `pinv` fallback used | Consider PCA whitening; check for duplicate columns |
| N < p (more features than samples) | Covariance is rank-deficient | Use LOF / ECOD for high-dim small-N |
| Non-Gaussian features | χ² distance approximation breaks; FPR inflated on skewed columns | Transform skewed features (log, Box-Cox) before scoring |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~1% | Chi-square threshold at 99.9 pct under normality |
| Lognormal | ~10-15% | Non-Gaussian features inflate FPR |
| Poisson | ~3-5% | Discrete; approximately normal at high λ |
| Beta | ~3-5% | Bounded; approximately normal-ish |
| Pareto | ~15-25% | Heavy tail breaks chi-square approximation |
| Exponential | ~10% | Right-skew |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~1% |
| Lognormal | (default) | ~10-15% |
| Poisson | (default) | ~3-5% |
| Beta | (default) | ~3-5% |
| Pareto | (default) | ~15-25% |
| Exponential | (default) | ~10% |

## Citation

Mahalanobis, P.C. (1936). On the generalised distance in statistics. *Proceedings of the National Institute of Sciences of India*, 2(1), 49–55.

Implementation: `packages/dqt/src/dqt/algorithms/outliers_multi/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="dim_sellers",
    detector_slug="mahalanobis_distance",
    params={'p_threshold': 0.001},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Assumes multivariate normality.
- Cannot handle collinear features without regularisation.
- Heavy-tailed columns inflate FPR.
