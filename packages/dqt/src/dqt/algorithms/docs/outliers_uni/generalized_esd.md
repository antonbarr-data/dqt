# Generalized ESD (Rosner) (`generalized_esd`)

**Group:** `outliers_uni` · **Kind:** `sample` · **Version:** `1` · **Min N:** 10

## What it computes

Iteratively removes the most-extreme value, computes a critical lambda from the t-distribution, and declares `n_outliers` as the largest i for which the test statistic exceeds λ_i. Score is `n_outliers / N`.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `max_outliers` | `int` | `0` | Max outliers to test for; 0 = auto: max(10, N/10) |
| `alpha` | `float` | `0.05` | Significance level for each individual ESD test |

## Assumptions

- Numeric column is approximately normal.
- Up to `max_outliers` outliers may be present (default auto: max(10, N/10)).
- Sample size ≥ 10 plus 2 × expected outlier count.

## When it works well

- Small-to-medium samples (10–500) from approximately normal columns with multiple outliers.
- Audit / financial data where a precise count of anomalous records is needed.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Non-normal data | GESD assumes normality like Grubbs; FPR > 10% on lognormal | Use `mad_outlier_fraction` for non-normal data |
| k too large | Setting k close to N/2 iterates until k outliers are 'found' | Set `max_outliers` to expected max (1–5% of N) |
| N < 25 | Critical values unreliable for small samples | Increase sample size |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~5% | Controlled by alpha across k iterations |
| Lognormal | ~15-30% | Assumes normality; FPR inflated |
| Poisson | ~5-8% | Discrete; mild inflation |
| Beta | ~5% | Bounded |
| Pareto | ~25-40% | Heavy tail; very inflated |
| Exponential | ~10-20% | Right-skew |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~5% |
| Lognormal | (default) | ~15-30% |
| Poisson | (default) | ~5-8% |
| Beta | (default) | ~5% |
| Pareto | (default) | ~25-40% |
| Exponential | (default) | ~10-20% |

## Citation

Rosner, B. (1983). *Percentage Points for a Generalized ESD Many-Outlier Procedure*. Technometrics, 25(2), 165–172.

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
    detector_slug="generalized_esd",
    params={'max_outliers': 0, 'alpha': 0.05},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Normality required for the p-value calibration.
- Computational cost O(k × n); cap k at ~20.
