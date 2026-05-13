# KS drift (`ks_pvalue`)

**Group:** `drift` · **Kind:** `sample` · **Version:** `1` · **Min N:** 30

## What it computes

Runs `scipy.stats.ks_2samp` between reference and current arrays. Reports `1 - p_value` so higher = more evidence of drift. Default thresholds: warn at p < 0.05, fail at p < 0.01.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | Stateless detector — thresholds come from `STAT_SCALES` |

## Assumptions

- The column is continuous numeric.
- Reference and current samples are independent.
- Sample size is moderate; the test is over-powered at very large N (>10k).

## When it works well

- Default drift test on continuous columns of unknown shape.
- Automated baselining pipelines — no parameter tuning required.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Very large N (> 10 000) | Detects statistically significant but operationally irrelevant drift | Use `wasserstein_1` for magnitude |
| Ties (integer / categorical data) | p-value inflated; KS conservative on ties | Use `chi_square_drift` for categorical; `psi` for binned continuous |
| Different sample sizes | Power dominated by the smaller sample | Subsample to equal size or use `psi` |
| Multiple columns tested without correction | p-value inflation: ~1 false positive per 20 columns at α=0.05 | Apply Benjamini-Hochberg correction across columns |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~5% | Calibrated at α=0.05 |
| Lognormal | ~5% | Distribution-free; FPR well-calibrated |
| Poisson | ~5% | Ties slightly inflate but generally well-calibrated |
| Beta | ~5% | Distribution-free |
| Pareto | ~5% | Distribution-free |
| Exponential | ~5% | Distribution-free |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~5% |
| Lognormal | (default) | ~5% |
| Poisson | (default) | ~5% |
| Beta | (default) | ~5% |
| Pareto | (default) | ~5% |
| Exponential | (default) | ~5% |

## Citation

Kolmogorov, A. N. (1933) & Smirnov, N. V. (1948); two-sample test wrapping `scipy.stats.ks_2samp`.

Implementation: `packages/dqt/src/dqt/algorithms/drift/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_bookings",
    column_name="amount_paid_usd",
    detector_slug="ks_pvalue",
    params={},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Distribution-free but reports a hypothesis test, not a magnitude.
- Over-powered at large N.
- Conservative on tied / discrete data.
