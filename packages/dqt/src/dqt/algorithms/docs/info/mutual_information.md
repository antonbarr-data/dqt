# Normalised mutual information (`mutual_information`)

**Group:** `info` · **Kind:** `sample` · **Version:** `1` · **Min N:** 100

## What it computes

Builds a 2D joint histogram between reference and current arrays using `n_bins` bins, then computes `NMI = MI / sqrt(H_ref × H_curr)` ∈ `[0, 1]`. Score direction is `higher_is_better`: 1.0 = identical, lower = more drift.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `n_bins` | `int` | `20` | Number of equal-width bins for histogram approximation |

## Assumptions

- The column is continuous numeric or low-cardinality ordinal.
- Sample size ≥ 100 per window for stable histogram estimates.
- Bin count is set appropriately for the column's range and cardinality (default 20).

## When it works well

- Distribution-shape similarity, including non-linear changes that mean/quantile checks miss.
- Bounded score [0, 1] comparable across columns.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Wrong bin count (n_bins) | Too few miss shape changes; too many produce noise | Default 20; increase to 50 for wide-range columns, 5-10 for narrow |
| Small sample (< 100 rows) | NMI estimate noisy; fluctuates between runs | Require N ≥ 100; use `ks_pvalue` for small samples |
| Score direction confusion | NMI is `higher_is_better`; 0.3 is a failure | Verify alerting reads direction correctly |
| High-cardinality column | Sparse bins inflate joint entropy; NMI drops without drift | Use `cramers_v` for categorical or `wasserstein_1` for high-cardinality numerics |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~5% | Histogram estimator variance |
| Lognormal | ~7% | Heavier tails increase variance |
| Poisson | ~6% | Discrete; bin boundary effects |
| Beta | ~5% | Bounded |
| Pareto | ~10-15% | Heavy tail; bin sparsity |
| Exponential | ~7% | Right-skew |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~5% |
| Lognormal | (default) | ~7% |
| Poisson | (default) | ~6% |
| Beta | (default) | ~5% |
| Pareto | (default) | ~10-15% |
| Exponential | (default) | ~7% |

## Citation

Cover, T.M. & Thomas, J.A. (2006). *Elements of Information Theory* (2nd ed.). Wiley-Interscience.

Implementation: `packages/dqt/src/dqt/algorithms/info/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="dim_sellers",
    column_name="tier",
    detector_slug="mutual_information",
    params={'n_bins': 20},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Sensitive to bin count and sample size.
- Direction is `higher_is_better` — be careful with alerting.
