# 質 dqt

**The Data Quality Tool for Agentic BI. Tells you the what and surfaces the why.**

[![Python ≥3.12](https://img.shields.io/badge/python-%E2%89%A53.12-blue?style=flat-square)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)
[![PyPI](https://img.shields.io/badge/pip%20install-dqtlib-orange?style=flat-square)](https://pypi.org/project/dqtlib/)
[![Release notes](https://img.shields.io/badge/release%20notes-v1.5.1-blue?style=flat-square)](docs/releases/README.md)

<!-- BENCHMARK_STATS_START -->
**64 detectors** across 5 families (drift, outlier, time series, distribution, rule) · best F1 **0.933** (holt_winters / wasserstein_1) · [full results](examples/benchmarks/results.csv)
<!-- BENCHMARK_STATS_END -->

dqt is a data quality tool built for **Agentic BI**: the world where agents, not just people, read your metrics and write your reports. It connects to your warehouse, imports your semantic layer from open formats ([Google OKF](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing) and [Apache Ossie](https://ossie.apache.org)), and wraps everything in a statistical quality harness with column-level lineage and causal explanations. The result is a grounded semantic layer you did not have to hand-write, plus guardrails that keep the metrics and reports your agents produce correct, explainable, and on-spec.

---

## The problem it solves

Without dqt: `orders.amount null_fraction >= 0.05 -- threshold exceeded`. Now what? Go dig through git log, dbt docs, warehouse history.

With dqt:

```
orders.amount null_fraction = 12.4% (baseline 0.3%)
Lineage: stg_payments -> orders -> revenue
Schema break in stg_payments 6h ago.
Causal candidate: stg_payments -> orders.amount (E-value 3.2, pending human review)
```

---

## Four layers

- **Statistical detectors** - MAD, double-MAD, isolation forest, KS, STL residuals, adjusted boxplot fences. Plus completeness, validity, freshness, schema-change, and SQL-assertion checks. Every detector returns `(verdict, score, plain_english)`.
- **Column-level lineage** - walks your dbt manifest and warehouse DDL with sqlglot. From any incident, automatic blast radius across downstream tables and metrics.
- **Google OKF / Apache Ossie import** - connect a Git repo of [Google OKF](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing) bundles or [Apache Ossie](https://ossie.apache.org) files. An LLM extracts datasets, columns, metrics, and playbooks; you review and select what to import against a live source. Datasets, metrics, and disabled checks land automatically via `dqt repo add`.
- **Causal discovery** - Granger causality, PCMCI+, Transfer Entropy across your metric time series. Edges are proposed, human-reviewed, then enter the production DAG annotated with lag, confidence, and E-values.

---

## Quick start

```bash
pip install dqtlib
```

```python
from dqt import Check, Runner, MemoryStore

check = Check(
    schema_name="public",
    table_name="orders",
    column_name="amount",
    detector_slug="mad_outlier_fraction",
)

result = Runner(MemoryStore()).run(check, adapter)
print(result.plain_english)
# "0.82% of values are outliers -- within the 1% warn threshold"
```

```bash
# Or from YAML
dqt run checks.yaml

# Exit codes: 0 = all pass, 2 = one or more failed
```

---

## Installation

```bash
pip install dqtlib                # core library + CLI
pip install "dqtlib[llm]"         # + LiteLLM provider (OKF/Ossie extraction; any LLM)
pip install "dqtlib[wiki]"        # + direct Anthropic Claude provider (deprecated LLM Wiki)
pip install "dqtlib[dashboard]"   # + local browser dashboard
pip install "dqtlib[reports]"     # + HTML profiling reports
pip install "dqtlib[causal]"      # + PCMCI+ causal discovery
pip install "dqtlib[all]"         # everything
```

Requires Python >= 3.12.

---

## Warehouse support

Built for ClickHouse and BigQuery first. Snowflake, Databricks, Postgres - WIP.

| Engine | Status |
|--------|--------|
| ClickHouse | Supported |
| BigQuery | Supported |
| PostgreSQL | Supported |
| DuckDB / CSV / Parquet | Supported |
| Snowflake | WIP |
| Databricks SQL | WIP |

All adapters are cost-guarded (`dryRun`/`EXPLAIN` before any query) and read-only.

---

## Integrations

- **dbt** - reads `manifest.json` and `semantic_models.yml` directly
- **Airflow / Dagster / Prefect** - runs as one Python task
- **OpenLineage** - ingests events from any non-dbt pipeline
- **Slack** - post check suite results to a channel via Incoming Webhook ([docs/api/notifications.md](docs/api/notifications.md))
- **Claude Code** - [Context7 plugin](https://claude.com/plugins/context7) for live dqt docs, [Superpowers](https://claude.com/plugins/superpowers) for agentic check-suite builds

---

## Documentation

| Doc | Description |
|-----|-------------|
| [Getting started](docs/getting-started.md) | First check in 5 min, drift detection, CLI, dashboard, quick-reference slug table |
| [Detectors reference](docs/api/detectors.md) | All detectors with parameters and examples |
| [YAML check format](docs/api/yaml-reference.md) | Complete YAML config reference |
| [CLI reference](docs/api/cli-reference.md) | All CLI commands including `dqt wiki`, `dqt report` |
| [Python API](docs/api/checks-and-runner.md) | Check model, CheckScope, Runner, MemoryStore |
| [Notifications](docs/api/notifications.md) | Slack suite reports, EmailNotifier, webhook setup |
| [Semantic import](docs/wiki.md) | Google OKF / Apache Ossie ingest (replaces LLM Wiki) |
| [Adapters](docs/api/adapters.md) | Warehouse adapter protocol |
| [Local dashboard](docs/dashboard.md) | Browser UI for check results |
| [Benchmarks](docs/benchmarks.md) | F1, recall, precision across 30 trials |
| [Architecture](docs/architecture/overview.md) | System design, module boundaries, project layout |
| [Comparison](docs/comparison.md) | dqt vs GE, Soda, Elementary, Dataplex |
| [Release notes](docs/releases/README.md) | Per-version changelog |

---

## About

[Anton Barr](https://www.linkedin.com/in/antonbar/) is an engineer and data geek with 25+ years building data systems. dqt is a personal project built by a practitioner who believes craft and precision are the same thing, and got tired of tools that answer *what* but never *why*.

質 (shitsu) - quality, substance, the inner nature of a thing. The kanji points to what something truly is, not how it appears. dqt is meant to work the same way: concerned with the truth of the data, not its surface. The mark is also a quiet acknowledgment of a tradition I have learned much from, one in which quality is one of its most distinguishing characteristics, and craft and precision are understood to be the same thing. - *Anton Barr*

---

## License

MIT - see [LICENSE](LICENSE).
