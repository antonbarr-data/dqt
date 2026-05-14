# One-Class SVM (`one_class_svm`)

**Group:** `outliers_multi` · **Kind:** `sample` · **Version:** `1` · **Min N:** 300

## What it computes

Trains `sklearn.svm.OneClassSVM` on the reference (RBF kernel by default). At score time returns the fraction of current rows classified as `-1` (outside the learned support).

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `nu` | `float` | `0.01` | Upper bound on training-outlier fraction |
| `kernel` | `str` | `"rbf"` | Kernel function: `rbf`, `linear`, `poly`, `sigmoid` |

## Assumptions

- Reference has ≥ 300 rows; OC-SVM is data-hungry.
- Feature dimensionality is moderate (≤ 50) — kernel-matrix cost grows quickly.
- `nu` matches the expected training-outlier fraction.

## When it works well

- Complex non-convex reference distributions where Mahalanobis is too restrictive.
- Multi-modal references where HBOS would smear bins across modes.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| nu parameter sensitivity | Wrong `nu` causes systematic over/under-flagging | Set `nu` to expected contamination (0.01–0.10) |
| Slow fit on large N | SVM fit is O(N²) to O(N³) | Subsample reference to ≤ 5000 rows for fitting |
| Kernel selection | RBF is default; wrong kernel degrades performance on structured data | Try `linear` for near-linear boundaries |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~5% | nu=0.05 calibration; matches expected outlier rate |
| Lognormal | ~10-15% | Heavy tail; bandwidth issue |
| Poisson | ~5% | Discrete |
| Beta | ~5% | Bounded |
| Pareto | ~15-25% | Heavy tail; kernel struggles |
| Exponential | ~8-10% | Right-skew |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~5% |
| Lognormal | (default) | ~10-15% |
| Poisson | (default) | ~5% |
| Beta | (default) | ~5% |
| Pareto | (default) | ~15-25% |
| Exponential | (default) | ~8-10% |

## Citation

Schölkopf, B., Platt, J.C., Shawe-Taylor, J., Smola, A.J., & Williamson, R.C. (2001). Estimating the support of a high-dimensional distribution. *Neural Computation*, 13(7), 1443–1471.

Implementation: `packages/dqt/src/dqt/algorithms/outliers_multi/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_gigs",
    detector_slug="one_class_svm",
    params={'nu': 0.01, 'kernel': 'rbf'},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Training cost O(N²)–O(N³); subsample for large references.
- No calibrated probability — binary in/out decision.
- `nu` is an upper bound, not an exact calibration.
