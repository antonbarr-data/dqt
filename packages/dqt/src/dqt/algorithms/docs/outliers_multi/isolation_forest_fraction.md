# Isolation Forest (`isolation_forest_fraction`)

**Group:** `outliers_multi` · **Kind:** `sample` · **Version:** `1` · **Min N:** 100

## What it computes

Fits `sklearn.ensemble.IsolationForest` on numeric columns of the reference. Returns the fraction of current rows the model classifies as anomalies (`prediction == -1`).

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `contamination` | `float` | `0.05` | Expected fraction of anomalies in the reference set |

## Assumptions

- Numeric features with ≥ 2 dimensions.
- Reference contains ≥ 100 rows for stable tree ensemble.
- `contamination` matches the expected outlier rate in the reference.

## When it works well

- Multi-column tables where anomalies come from unusual feature *combinations*.
- High-dimensional features (embeddings, wide fact tables).

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Single-column input | Degenerates to a 1-D tree density estimator | Use `mad_outlier_fraction` for single-column outliers |
| High contamination in reference | Baseline threshold shifts upward; real outliers masked | Pre-clean reference with a single-pass MAD filter |
| Large N slow fit | Tree ensemble fit is O(N × trees × depth) | Subsample reference to 10k for fitting |
| Categorical features | Requires numeric input | One-hot encode categoricals first |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~5% | Tree-based partition; matches contamination |
| Lognormal | ~6-8% | Heavy tail mildly inflates |
| Poisson | ~5% | Discrete; tree partitions handle well |
| Beta | ~5% | Bounded; well behaved |
| Pareto | ~8-12% | Heavy tail |
| Exponential | ~6-8% | Right-skew |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~5% |
| Lognormal | (default) | ~6-8% |
| Poisson | (default) | ~5% |
| Beta | (default) | ~5% |
| Pareto | (default) | ~8-12% |
| Exponential | (default) | ~6-8% |

## Citation

Liu, F. T., Ting, K. M., & Zhou, Z.-H. (2008). Isolation Forest. *ICDM 2008*, 413–422.

Implementation: `packages/dqt/src/dqt/algorithms/outliers_multi/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_gigs",
    detector_slug="isolation_forest_fraction",
    params={'contamination': 0.05},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- `contamination` is a hyperparameter, not a calibrated probability.
- Treats features axis-aligned; may miss anomalies in correlated subspaces.
