# MMD (kernel two-sample) (`mmd`)

**Group:** `drift` · **Kind:** `sample` · **Version:** `1` · **Min N:** 50

## What it computes

Sub-samples ≤500 rows per side, estimates RBF bandwidth via the median heuristic, and computes the biased MMD² estimator. Score is clipped to `[0, 1]`.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | Stateless detector — thresholds come from `STAT_SCALES` |

## Assumptions

- All input columns are numeric (categorical must be encoded).
- Median-heuristic bandwidth is reasonable for the data scale.
- Sample sizes are at least 50 per window; the implementation caps at 500 for tractability.

## When it works well

- Multivariate drift on entire feature sets without column-wise binning.
- Detecting non-linear distributional shifts that PSI/KL miss.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| O(n²) kernel computation | Slow on large samples; capped at 500 subsampled rows | Increase `_MAX_SUBSAMPLE` if memory allows; or use `ks_pvalue` for speed |
| All-zero features | RBF kernel evaluates to 1.0 for all pairs; MMD=0 | Remove zero-variance columns before scoring |
| gamma=0 (all-identical reference) | Fallback bandwidth of 1.0; may not reflect true drift | Apply a uniqueness / variance check upstream |
| Score interpretation | Clip to [0,1] via empirical max; clipping is heuristic | Use `ks_pvalue` p-value for statistical significance |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~5% | Median heuristic bandwidth works well |
| Lognormal | ~8-12% | Heavy tail challenges the kernel bandwidth |
| Poisson | ~6% | Discrete; mild bandwidth issue |
| Beta | ~5% | Bounded |
| Pareto | ~12-18% | Heavy tail |
| Exponential | ~7-10% | Skewed |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~5% |
| Lognormal | (default) | ~8-12% |
| Poisson | (default) | ~6% |
| Beta | (default) | ~5% |
| Pareto | (default) | ~12-18% |
| Exponential | (default) | ~7-10% |

## Citation

Gretton, A., Borgwardt, K.M., Rasch, M.J., Schölkopf, B., & Smola, A. (2012). A Kernel Two-Sample Test. *Journal of Machine Learning Research*, 13, 723–773.

Implementation: `packages/dqt/src/dqt/algorithms/drift/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_gigs",
    detector_slug="mmd",
    params={},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- O(n²) kernel matrix; subsampling required.
- No analytic null distribution at this implementation level.
- Bandwidth via median heuristic is robust but not optimal for all shapes.
