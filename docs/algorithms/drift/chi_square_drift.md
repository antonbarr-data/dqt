# Chi-square drift (`chi_square_drift`)

**Group:** `drift` · **Kind:** `sample` · **Version:** `1` · **Min N:** 50

## What it computes

Builds expected counts from reference frequencies and runs `scipy.stats.chisquare` against observed counts in the current window. Score = `1 - p_value`.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | Stateless detector — thresholds come from `STAT_SCALES` |

## Assumptions

- The column is categorical or low-cardinality integer.
- Expected cell count is ≥ 5 per category (otherwise the chi-square approximation breaks).
- Sample sizes are comparable; very different N inflates the statistic.

## When it works well

- Status codes, country codes, low-cardinality categorical columns (2–50 values).
- Monitoring label distributions in ML prediction outputs.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Expected cell count < 5 | Chi-square approximation breaks; p-value unreliable | Merge rare categories; use `cramers_v` which handles sparsity |
| Continuous data | Binning is arbitrary and introduces sensitivity | Use `ks_pvalue` or `wasserstein_1` for continuous columns |
| High-cardinality categoricals (> 50) | Degrees of freedom explode; very small p-values even for minor shifts | Limit to top-K + 'other' |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | N/A | Categorical detector — not applicable |
| Lognormal | N/A | Categorical detector — not applicable |
| Poisson | ~5% | Low-cardinality integer; matches α=0.05 |
| Beta | N/A | Continuous — not applicable |
| Pareto | N/A | Continuous — not applicable |
| Exponential | N/A | Continuous — not applicable |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | N/A |
| Lognormal | (default) | N/A |
| Poisson | (default) | ~5% |
| Beta | (default) | N/A |
| Pareto | (default) | N/A |
| Exponential | (default) | N/A |

## Citation

Pearson, K. (1900). On the criterion that a given system of deviations from the probable in the case of a correlated system of variables is such that it can be reasonably supposed to have arisen from random sampling. *Philosophical Magazine*, 50(302), 157–175.

Implementation: `packages/dqt/src/dqt/algorithms/drift/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_reviews",
    column_name="rating",
    detector_slug="chi_square_drift",
    params={},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Categorical only.
- Cardinality-sensitive; rare categories distort the statistic.
- Reports a test statistic, not an effect-size; pair with `cramers_v` for magnitude.
