# dqtlib

**Open-source data quality, lineage, semantic layer & causality — for dbt, warehouses and data lakes.**

pip-installable Python library for watching dbt-built warehouses and any SQL warehouse for statistical drift, anomalies, silent regressions, and explaining *why* metrics moved.

```bash
pip install dqtlib
```

The import name is `dqt`:

```python
from dqt import Check, Runner, MemoryStore
```

Full documentation and examples: https://github.com/antonbarr-data/dqt

## Quality

All 64 detectors are benchmarked against labeled synthetic datasets. Results are reproducible by anyone:

<!-- NUMBERS_START -->
Median F1: 1.00 | Detectors with F1 >= 0.8: 52/64 | Detectors with F1 >= 0.6: 58/64
<!-- NUMBERS_END -->

Per-detector breakdown: [examples/benchmarks/results_summary.md](examples/benchmarks/results_summary.md)

Reproduce locally:
```bash
python scripts/run_benchmark_suite.py --quick
python scripts/generate_benchmark_summary.py
```

## Adapters

| Adapter | Nightly Tests |
|---------|--------------|
| PostgreSQL | ![postgres](https://img.shields.io/badge/postgres-tested-7FB394) |
| ClickHouse | ![clickhouse](https://github.com/antonbarr-data/dqt/actions/workflows/live-adapter-tests.yml/badge.svg?job=clickhouse) |
| Snowflake | ![snowflake](https://github.com/antonbarr-data/dqt/actions/workflows/live-adapter-tests.yml/badge.svg?job=snowflake) |
| BigQuery | ![bigquery](https://github.com/antonbarr-data/dqt/actions/workflows/live-adapter-tests.yml/badge.svg?job=bigquery) |
| Databricks | ![databricks](https://github.com/antonbarr-data/dqt/actions/workflows/live-adapter-tests.yml/badge.svg?job=databricks) |
| MySQL | ![mysql](https://img.shields.io/badge/mysql-tested-7FB394) |
| Redshift | ![redshift](https://img.shields.io/badge/redshift-tested-7FB394) |
| DuckDB | ![duckdb](https://img.shields.io/badge/duckdb-tested-7FB394) |
| Trino | ![trino](https://img.shields.io/badge/trino-tested-7FB394) |

## Detector documentation

64 statistical detectors across 10 groups — drift, outliers, time series, distribution, information theory, pattern, referential, schema, basic, and custom.

Every detector has a structured page at [`docs/algorithms/<group>/<slug>.md`](docs/algorithms/README.md) covering:

- What it computes and its parameters
- When it works well and when it fails (with concrete failure-mode table)
- Default-threshold calibration — empirical FPR across six canonical data shapes (Normal, Lognormal, Poisson, Beta, Pareto, Exponential)
- Recommended thresholds per data shape
- Canonical citation and runnable Python API example

Browse the full catalog: [docs/algorithms/README.md](docs/algorithms/README.md)
