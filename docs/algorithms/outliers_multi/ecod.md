# ECOD (`ecod`)

**Group:** `outliers_multi` · **Kind:** `sample` · **Version:** `1` · **Min N:** 200

## What it computes

For each row sums `-log(min(F̂_j(x_j), 1 - F̂_j(x_j)))` across features (empirical CDF tail probabilities). Stores the reference 99th-percentile score as threshold and returns the fraction of current rows exceeding it.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| *(none)* | — | — | Stateless detector — thresholds come from `STAT_SCALES` |

## Assumptions

- Numeric tabular data with ≥ 2 features.
- Reference contains at least 200 rows for stable ECDF estimates.
- Features are independent enough that an additive aggregation makes sense.

## When it works well

- High-dimensional tabular data (the default multivariate detector when n_features ≥ 10).
- Heterogeneous numeric features — assumption-free, no kernel bandwidth.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Skewed marginal distributions | ECDF asymmetric on skewed data | Best for heavy-tailed data; log-transform for revenue/latency |
| Requires N > 50 per feature | ECDF estimates noisy for small N | Increase baseline window |
| Correlational outliers | ECOD scores each dimension independently | Use `mahalanobis_distance` or `lof` for correlated subspaces |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~5% | Tail probability threshold at 99th pct |
| Lognormal | ~5% | Excellent on heavy-tailed data |
| Poisson | ~6% | Discrete; threshold may be conservative |
| Beta | ~5% | Bounded |
| Pareto | ~5-8% | Tail probabilities adapt |
| Exponential | ~5% | Distribution-free |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~5% |
| Lognormal | (default) | ~5% |
| Poisson | (default) | ~6% |
| Beta | (default) | ~5% |
| Pareto | (default) | ~5-8% |
| Exponential | (default) | ~5% |

## Citation

Li, Z., Zhao, Y., Botta, N., Ionescu, C., & Hu, X. (2022). ECOD: Unsupervised Outlier Detection Using Empirical CDF Functions. *IEEE Transactions on Knowledge and Data Engineering*, 35(12), 12181–12193.

Implementation: `packages/dqt/src/dqt/algorithms/outliers_multi/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_bookings",
    detector_slug="ecod",
    params={},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Treats features independently; misses correlation-only anomalies.
- Needs reference with ≥ 200 rows for stable tail estimates.
