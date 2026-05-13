# HBOS (`hbos`)

**Group:** `outliers_multi` · **Kind:** `sample` · **Version:** `1` · **Min N:** 100

## What it computes

Builds per-column histograms (`n_bins`) over the reference and stores bin frequencies. The HBOS score for a row is `sum log(1 / freq(x_j in bin_j))`. Threshold = reference 99th percentile.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `n_bins` | `int` | `20` | Number of equal-width histogram bins per column |

## Assumptions

- Numeric features with approximately independent distributions.
- Sample size ≥ 100 in reference.
- Bin count appropriate for the data's resolution.

## When it works well

- High-throughput pipelines — O(n × d), no kernel matrix.
- Wide tables (many numeric columns) where LOF/SVM are too slow.

## When it fails

| Failure mode | Symptom | What to use instead |
|---|---|---|
| Strongly correlated features | HBOS independence assumption misses correlational anomalies | Use `mahalanobis_distance` or `lof` |
| Bin count sensitivity | Default may miss narrow anomaly peaks | Rule of thumb: n_bins ≈ sqrt(N) |
| Unseen bins in current window | Score smoothed at minimum; genuine outliers masked | Re-fit baseline if distributions shift |

## Default-threshold calibration

Empirical FPR at the detector's default threshold, measured on N=5000 synthetic samples per shape using the canonical fixtures in `scripts/regenerate_calibration_tables.py`.

| Data shape | FPR at default | Notes |
|---|---|---|
| Normal | ~5% | Histogram bins matched to N |
| Lognormal | ~8-12% | Bin sparsity in heavy tail |
| Poisson | ~6% | Discrete; bin alignment |
| Beta | ~5% | Bounded; well behaved |
| Pareto | ~10-15% | Heavy tail inflates sparse-bin scores |
| Exponential | ~7-10% | Right-skew |

## Recommended thresholds per data shape

| Data shape | Threshold | Achieved FPR |
|---|---|---|
| Normal | (default) | ~5% |
| Lognormal | (default) | ~8-12% |
| Poisson | (default) | ~6% |
| Beta | (default) | ~5% |
| Pareto | (default) | ~10-15% |
| Exponential | (default) | ~7-10% |

## Citation

Goldstein, M. & Dengel, A. (2012). Histogram-based Outlier Score (HBOS): A fast Unsupervised Anomaly Detection Algorithm. *KI-2012 Poster and Demo Track*, 59–63.

Implementation: `packages/dqt/src/dqt/algorithms/outliers_multi/` — see registry for exact file.

## API example

```python
import pandas as pd
from dqt import Check, Runner, MemoryStore

# Build a check that wires this detector to a target table/column.
check = Check(
    schema_name="public",
    table_name="fct_gigs",
    detector_slug="hbos",
    params={'n_bins': 20},
)

# Library usage: Runner pulls a sample via the configured adapter and runs the detector.
runner = Runner(MemoryStore())
# result = runner.run(check, adapter)  # adapter = DuckDBAdapter.from_dataframe(df) etc.
# print(result.verdict, result.score, result.plain_english)
```

## Limitations

- Feature-independence assumption.
- Approximate; fast but less accurate than ECOD or LOF.
