# dqt

> Open-source data quality, observability, semantic, and causality library + service.
> Watches your warehouse for drift, anomalies, and silent regressions — and explains *why* things moved.

`dqt` is a pip-installable Python library at the core, with a FastAPI service and a Next.js UI on top. It supersets [Great Expectations](https://greatexpectations.io/), [Soda](https://www.soda.io/), and [Elementary](https://www.elementary-data.com/), adds the full statistical / ML detector zoo from the literature, plus a semantic layer, column-level lineage, an automatically-discovered causal driver-tree DAG, an HITL review loop, and an AI agent that explains incidents grounded in [Pearl's ladder of causation](https://en.wikipedia.org/wiki/Causal_inference#The_Ladder_of_Causation).

## Quick start

```bash
pip install dqt

# In a notebook or script
import dqt
from dqt.adapters import postgres

src = postgres.connect(host="localhost", database="analytics", user="reader")
src.health_check()                    # 6-step checklist

# Auto-baseline a column
checks = dqt.autobaseline(src, dataset="public.fct_orders")

# Run them
results = [dqt.run(c, src) for c in checks]
for r in results:
    print(r.detector, r.verdict, r.score)
```

## What's in the library

- **Adapters** — Postgres, MySQL, ClickHouse, BigQuery, Snowflake, Redshift, Databricks SQL, DuckDB, Trino. Same protocol, read-only, cost-bounded.
- **Algorithms** — every method in [`docs/algorithms/`](docs/algorithms/): distribution diagnostics (KS, Anderson–Darling, dip), univariate outliers (MAD, double-MAD, GESD), multivariate outliers (Isolation Forest, ECOD, LOF, autoencoders), time-series (STL, BOCPD, matrix profile, Prophet), drift (PSI, Wasserstein, MMD, KL/JS), causal discovery (PCMCI+, PC, Granger, Transfer Entropy, NOTEARS), Pearl's do-calculus.
- **Checks** — declarative YAML, strict superset of SodaCL. Auto-baseliner, plain-English authoring.
- **Lineage** — column-level via sqlglot + dbt manifest + OpenLineage.
- **Semantic** — metric definitions as contracts; dbt semantic-layer compatible.
- **Causality** — discovered DAG, HITL review, Shapley attribution, do-calculus, E-value sensitivity.
- **Agent** — LLM-backed, Pearl-ladder grounded, every claim cited.
- **Compatibility** — `dqt.compat.gx` / `.soda` / `.elementary` to ingest existing test suites and dbt artifacts.

## What's in the apps

- `apps/server/` — FastAPI multi-tenant SaaS deployment.
- `apps/worker/` — arq-backed scheduler and AI agent loop.
- `apps/web/` — Next.js 14 power-user UI.

You don't need any of these to use the library. They're a reference deployment.

## Use it standalone

The library imports without Postgres, without Redis, without FastAPI. It's designed to be embedded in:
- Notebooks and scripts
- Airflow / Dagster / Prefect tasks
- CI pipelines (data quality gates on PRs)
- Anywhere you have a SQL warehouse and a Python interpreter

## Use it as a service

```bash
git clone https://github.com/<org>/dqt
cd dqt
./run_local/start.sh         # Postgres + Redis + MailHog in Docker; demo data seeded
make dev                     # server + worker + web with hot reload

open http://localhost:3000
```

See [`docs/`](docs/) for the full setup, deployment, and authoring guides.

## Project structure

```
packages/dqt/         # the library (MIT, pip-publishable)
packages/dqt-cli/     # CLI tool
apps/server/          # FastAPI service
apps/worker/          # arq worker
apps/web/             # Next.js UI
shared/               # cross-cutting JSON schemas + generated code
docs/                 # documentation
examples/             # runnable library examples
```

## Contributing

Read [`.ai/rules/`](.ai/rules/) before opening a PR — especially:
- [`general-rules.mdc`](.ai/rules/general-rules.mdc)
- [`library-vs-server.mdc`](.ai/rules/library-vs-server.mdc) — the hardest rule
- [`algorithms.mdc`](.ai/rules/algorithms.mdc) — detector contract
- [`open-source.mdc`](.ai/rules/open-source.mdc) — public API + semver discipline

CI gates: `make test-lib` (<60s), lint (ruff + mypy strict on the library), typecheck.

New algorithm? See [`algorithms.mdc`](.ai/rules/algorithms.mdc) for the five required tests.

## License

MIT. See [`LICENSE`](LICENSE).

## Acknowledgements

Inspired by — and where reasonable, compatible with:
- [Great Expectations](https://github.com/great-expectations/great_expectations)
- [Soda Core / SodaCL](https://github.com/sodadata/soda-core)
- [Elementary](https://github.com/elementary-data/elementary)
- [Tigramite](https://github.com/jakobrunge/tigramite) for PCMCI+
- [DoWhy](https://github.com/py-why/dowhy) for do-calculus
- [PyOD](https://github.com/yzhao062/pyod) for outlier algorithms
- [STUMPY](https://github.com/TDAmeritrade/stumpy) for matrix profile

And by Judea Pearl's *The Book of Why*, which is the reason the agent operates the ladder of causation explicitly.
