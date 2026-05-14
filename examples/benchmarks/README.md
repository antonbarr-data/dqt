# dqt Benchmark Suite

Reproducible benchmark results for all 64 dqt detectors against labeled synthetic datasets.

## Reproduce

```bash
# Install deps
pip install dqtlib numpy pandas scipy scikit-learn statsmodels stumpy

# Generate synthetic fixtures (one-time)
python scripts/generate_benchmark_data.py

# Run all 64 detectors
python scripts/run_benchmark_suite.py --quick

# Regenerate summary table and update README numbers
python scripts/generate_benchmark_summary.py
```

## Notebooks

| Notebook | Detectors | Group |
|----------|-----------|-------|
| [01_outliers_univariate.ipynb](01_outliers_univariate.ipynb) | 9 | outliers_uni |
| [02_outliers_multivariate.ipynb](02_outliers_multivariate.ipynb) | 6 | outliers_multi |
| [03_drift_distribution.ipynb](03_drift_distribution.ipynb) | 8 | drift |
| [04_changepoint_timeseries.ipynb](04_changepoint_timeseries.ipynb) | 7 | timeseries |
| [05_association.ipynb](05_association.ipynb) | 2 | info |
| [06_basic.ipynb](06_basic.ipynb) | 27 | basic |
| [07_referential_schema_pattern.ipynb](07_referential_schema_pattern.ipynb) | 3 | referential / schema / pattern |
| [08_custom.ipynb](08_custom.ipynb) | 2 | custom |

## Results

Full per-detector results: [results_summary.md](results_summary.md) (auto-generated — run `generate_benchmark_summary.py` to refresh).

## Dataset manifest

All fixtures are generated deterministically from seed 42 via `scripts/generate_benchmark_data.py`. The `--quick` flag uses only in-memory seeded RNG; no file I/O or network required.

| Fixture | Rows | Labels | Generator |
|---------|------|--------|-----------|
| synthetic_normal (N(0,1)) | 5,000 | 1% anomalies at ±10σ | `generate_shapes()` |
| synthetic_lognormal | 5,000 | 1% anomalies | `generate_shapes()` |
| synthetic_poisson | 5,000 | 1% anomalies | `generate_shapes()` |
| synthetic_beta | 5,000 | 1% anomalies | `generate_shapes()` |
| synthetic_pareto | 5,000 | 1% anomalies | `generate_shapes()` |
| synthetic_exponential | 5,000 | 1% anomalies | `generate_shapes()` |
| orders_dirty | 50,000 | 50 outliers | `generate_orders_dirty()` |
| daily_metrics_dirty | 180 days | 4 changepoints at days 30, 60, 120, 150 | `generate_daily_metrics()` |
