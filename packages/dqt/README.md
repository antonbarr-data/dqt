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

## Detector documentation

64 statistical detectors across 10 groups — drift, outliers, time series, distribution, information theory, pattern, referential, schema, basic, and custom.

Every detector has a structured page at [`docs/algorithms/<group>/<slug>.md`](docs/algorithms/README.md) covering:

- What it computes and its parameters
- When it works well and when it fails (with concrete failure-mode table)
- Default-threshold calibration — empirical FPR across six canonical data shapes (Normal, Lognormal, Poisson, Beta, Pareto, Exponential)
- Recommended thresholds per data shape
- Canonical citation and runnable Python API example

Browse the full catalog: [docs/algorithms/README.md](docs/algorithms/README.md)
