# Local Outlier Factor (`lof`)

**Group:** `outliers_multi` · **Kind:** `sample` · **Version:** `1` · **Min N:** 100

## What it computes

Trains `sklearn.neighbors.LocalOutlierFactor` (novelty mode) on the reference. Records the 99th-percentile negative LOF score as threshold. At score time the fraction of current rows above threshold is returned.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `n_neighbors` | `int` | `20` | Number of neighbours for local density estimation; capped to N-1 |

## Assumptions

- Numeric features with moderate dimensionality (2–20).
- Nearest-neighbour distance is meaningful (no curse of dimensionality).
- `n_neighbors` is between 10 and 50 for typical data.

## When it works well

- Datasets with non-convex or irregular cluster shapes where Mahalanobis misses intra-cluster outliers.
- Density varies across feature space — LOF adapts the estimate locally.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Very high dimensions (> 30 features) | NN distances concentrate; LOF loses contrast | Use `ecod` or `isolation_forest_fraction` |
| Large scoring batches (> 50k rows) | `score_samples` is O(n × k) | Use `hbos` for throughput-sensitive pipelines |
| k selection | Default 20 may be too small for sparse or too large for dense | Use k ≈ max(5, ceil(sqrt(N))) |
| Slow on high-dim | LOF is O(N²) in naive form | Use HBOS or ECOD for N > 10k |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~5% | k=20 default |
| Lognormal | ~6-8% | Mild tail effect |
| Poisson | ~6% | Discrete; density estimates noisy |
| Beta | ~5% | Bounded |
| Pareto | ~10-15% | Heavy tail; NN distances inflated |
| Exponential | ~7% | Right-skew |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~5% |
| Lognormal | (default) | ~6-8% |
| Poisson | (default) | ~6% |
| Beta | (default) | ~5% |
| Pareto | (default) | ~10-15% |
| Exponential | (default) | ~7% |

## Citation

Breunig, M.M., Kriegel, H-P., Ng, R.T., & Sander, J. (2000). LOF: Identifying Density-Based Local Outliers. *ACM SIGMOD Record*, 29(2), 93–104.

Implementation: `packages/dqt/src/dqt/algorithms/outliers_multi/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_gigs",
    detector_slug="lof",
    params={'n_neighbors': 20},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Curse of dimensionality limits use above ~20 features.
- O(N²) cost without approximate NN structures.
- Score is rank-based, not calibrated probability.
