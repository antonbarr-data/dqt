# dqtlib

**A Data Questioning Tool that tells you the what and surfaces the why.**

Unifies your scattered data into one source of truth. Upgrades your existing models, dashboards, and queries into a causal semantic layer you didn't have to write. Picks up on trends and surfaces business insights, all wrapped in a quality harness that puts guardrails on the AI so the reports it generates stay on-spec.

```bash
pip install dqtlib
```

The import name is `dqt`:

```python
from dqt import Check, Runner, MemoryStore
```

Full documentation and examples: https://github.com/antonbarr-data/dqt

## Quality

All 64 detectors are benchmarked against labeled synthetic datasets. Benchmark scripts and raw results live in the GitHub repo and are run on every release:

Median F1: 1.00 | Detectors with F1 >= 0.8: 52/64 | Detectors with F1 >= 0.6: 58/64

Per-detector breakdown: [examples/benchmarks/results_summary.md](https://github.com/antonbarr-data/dqt/blob/main/examples/benchmarks/results_summary.md)

Reproduce by cloning the repo and running:
```bash
python scripts/run_benchmark_suite.py --quick
python scripts/generate_benchmark_summary.py
```

## Adapters

Six adapters ship in v1.0. Nightly CI runs against live credentials for the cloud warehouses.

| Adapter | CI |
|---------|-----|
| PostgreSQL (local) | bundled — no credentials needed |
| ClickHouse | ![clickhouse](https://github.com/antonbarr-data/dqt/actions/workflows/live-adapter-tests.yml/badge.svg?job=clickhouse) |
| Snowflake | ![snowflake](https://github.com/antonbarr-data/dqt/actions/workflows/live-adapter-tests.yml/badge.svg?job=snowflake) |
| BigQuery | ![bigquery](https://github.com/antonbarr-data/dqt/actions/workflows/live-adapter-tests.yml/badge.svg?job=bigquery) |
| Databricks | ![databricks](https://github.com/antonbarr-data/dqt/actions/workflows/live-adapter-tests.yml/badge.svg?job=databricks) |
| Local (DuckDB) | bundled — no credentials needed |

## Detector documentation

64 statistical detectors across 10 groups — drift, outliers, time series, distribution, information theory, pattern, referential, schema, basic, and custom.

Every detector has a structured page at [`docs/algorithms/<group>/<slug>.md`](docs/algorithms/README.md) covering:

- What it computes and its parameters
- When it works well and when it fails (with concrete failure-mode table)
- Default-threshold calibration — empirical FPR across six canonical data shapes (Normal, Lognormal, Poisson, Beta, Pareto, Exponential)
- Recommended thresholds per data shape
- Canonical citation and runnable Python API example

Browse the full catalog: [docs/algorithms/README.md](docs/algorithms/README.md)
