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
