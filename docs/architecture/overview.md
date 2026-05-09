# Architecture overview

## C4 component diagram

```mermaid
C4Component
  title dqt system components

  Container_Boundary(lib, "packages/dqt (library — MIT, PyPI)") {
    Component(adapters, "Warehouse Adapters", "Python protocol", "DuckDB, Postgres, MySQL, BigQuery, Snowflake, Redshift, Databricks, ClickHouse, Trino")
    Component(algorithms, "Algorithms", "Python", "40+ detectors: basic, schema, drift, outliers_uni, outliers_multi, timeseries, referential")
    Component(runner, "Runner", "Python", "Orchestrates fit() + score() against an adapter; writes RunResult and Incident to store")
    Component(store, "Results Store", "Protocol", "MemoryStore (default, no deps) or PostgresStore (TimescaleDB)")
    Component(checks, "Check models", "Pydantic", "Check, CheckScope, CheckFilter, BaselineConfig")
    Component(lineage, "Lineage", "sqlglot + dbt", "Column-level lineage DAG, dbt manifest ingest, OpenLineage")
    Component(semantic, "Semantic layer", "Pydantic + YAML", "Metric definitions, embeddings, relationships")
    Component(causality, "Causality", "PCMCI+ / DoWhy", "Discovery pipeline, Shapley attribution, do-calculus")
    Component(governance, "Governance", "Python", "PolicyEngine, catalog, audit log, PII classification")
    Component(agent, "AI agent", "Anthropic SDK", "Pearl's ladder of causation, tool loop, citation-grounded output")
  }

  Container_Boundary(cli, "packages/dqt-cli (CLI)") {
    Component(manifest, "Manifest loader", "Pydantic + YAML", "version, source, semantic, checks")
    Component(cli_adapter, "CliDuckDBAdapter", "DuckDB", "Supports duckdb / csv / parquet sources")
    Component(run_cmd, "dqt run", "Typer + Rich", "Fit baselines, score all checks, print table or JSON")
  }

  Container_Boundary(server, "apps/server (FastAPI)") {
    Component(api, "REST API", "FastAPI", "/api/v1/* — sources, datasets, checks, incidents, metrics, causality, lineage")
    Component(ws, "WebSocket", "FastAPI", "/api/v1/ws — live incident feed, check-run progress")
    Component(middleware, "Auth middleware", "JWT + RLS", "tenant_id, user_id, role injected into request.state")
    Component(repos, "Repositories", "SQLAlchemy 2.x async", "TenantScopedRepository, TimescaleDB-aware")
    Component(workers, "arq Workers", "Redis-backed", "Scheduled check runs, agent loop, auto-baseliner")
    Component(notifiers, "Notifiers", "Plugin", "Slack, Teams, email, PagerDuty, Opsgenie, webhook")
  }

  Container_Boundary(web, "apps/web (Next.js 14)") {
    Component(ui_overview, "Overview / Incidents / Metrics", "React Server Components", "Fleet KPIs, incident list, metric detail")
    Component(ui_lineage, "Lineage / Causality", "Client components (SVG DAG)", "Column-level DAG, KL heatmap, Shapley attribution")
    Component(ui_tests, "Tests / Catalog", "React + React Query", "Check authoring, YAML preview, catalog search")
    Component(palette, "Cmd-K palette", "shadcn Command", "Quick nav, dataset search, agent shortcut")
  }

  Rel(run_cmd, manifest, "loads")
  Rel(run_cmd, cli_adapter, "builds")
  Rel(run_cmd, runner, "calls fit() + run()")
  Rel(runner, adapters, "sample() / aggregate()")
  Rel(runner, algorithms, "fit() / score()")
  Rel(runner, store, "save_run() / save_incident()")
  Rel(api, runner, "on-demand check execution")
  Rel(api, repos, "CRUD + time-series queries")
  Rel(workers, runner, "scheduled execution")
  Rel(workers, agent, "agent loop")
  Rel(notifiers, workers, "triggered on incident open")
  Rel(web, api, "OpenAPI-typed React Query client")
```

---

## Module descriptions

### Library (`packages/dqt/`)

| Module | Purpose |
|---|---|
| `dqt.adapters` | `WarehouseAdapter` protocol + engine implementations. Each adapter wraps ibis-framework for portable SQL, falls back to DuckDB for stat work on samples. |
| `dqt.algorithms` | All detectors. Each class has `slug`, `group`, `fit(ref_df) → state`, `score(curr_df, state) → DetectorResult`. Scales defined in `_scales.py`. |
| `dqt.checks` | `Check`, `CheckScope`, `CheckFilter`, `BaselineConfig` Pydantic models. YAML loader. JSON Schema at `checks/schema/check.schema.json`. |
| `dqt.runner` | `Runner` — orchestrates `fit()` + `score()`. Caches detector states by `check.id`. Auto-fits on first `run()` if no state exists. |
| `dqt.store` | `ResultsStore` protocol. `MemoryStore` (no deps, for notebooks/CI). `PostgresStore` (TimescaleDB, server). |
| `dqt.lineage` | sqlglot-based column-level lineage parsing. dbt manifest ingest. OpenLineage event ingest. `downstream_impact(incident)` for blast-radius. |
| `dqt.semantic` | Metric YAML definitions, embeddings (sentence-transformers), relationship edges. dbt `semantic_models.yml` compatible. |
| `dqt.causality` | PCMCI+ discovery pipeline, stability selection, Transfer Entropy annotation. Shapley decomposition over confirmed DAG. DoWhy do-calculus for hypotheticals. |
| `dqt.governance` | `PolicyEngine` — enforces YAML policies at runtime. Catalog (owner, domain, tags, classification, PII). Audit log. |
| `dqt.hitl` | Review queue for proposed causal edges, uncertain incident classifications, ambiguous mappings. Uncertainty sampling / query-by-committee. |
| `dqt.agent` | `LLMProvider` protocol. Anthropic Claude reference impl. Pearl's ladder of causation reasoning loop. Tools: `query_warehouse`, `run_detector`, `walk_lineage`, `get_dag_attribution`, `do_calculus`. |
| `dqt.compat` | Compatibility shims: `dqt.compat.gx` (Great Expectations), `dqt.compat.soda` (SodaCL YAML), `dqt.compat.elementary` (dbt artifacts). |

### Server (`apps/server/`)

| Module | Purpose |
|---|---|
| `dqt_server.auth` | JWT via fastapi-users. Roles: `viewer / editor / admin / oncall / sysadmin`. |
| `dqt_server.tenants` | Workspace management. All queries auto-scoped by `tenant_id`. |
| `dqt_server.sources` | Connection CRUD + 6-step health-check wizard backend. |
| `dqt_server.datasets` | Dataset metadata, column catalog, sample viewer. |
| `dqt_server.checks` | Check CRUD, on-demand runs, baseline scheduling. |
| `dqt_server.incidents` | Incident lifecycle (`open → investigating → resolved → closed`), comments, postmortems. |
| `dqt_server.metrics` | Semantic layer CRUD. Four auto-checks per metric (KS, Wasserstein-1, STL spike, BOCPD trend). |
| `dqt_server.causality` | DAG management, HITL review endpoints, attribution queries. |
| `dqt_server.lineage` | Lineage queries via recursive CTEs, coverage overlay. |
| `dqt_server.governance` | Catalog, policy CRUD, audit log viewer. |
| `dqt_server.oncall` | Schedules, rotations, escalation policies, routing rules. |
| `dqt_server.notifications` | Slack / Teams / email / SMS / PagerDuty / Opsgenie / webhook notifiers. |
| `dqt_server.workers` | arq tasks: scheduled check runs, agent loop, auto-baseliner, causal discovery refresh. |

---

## Data flow

```mermaid
flowchart TD
    W[("Warehouse\n(Postgres / BQ / Snowflake / ...)")] -->|sample / aggregate| A[WarehouseAdapter]
    A -->|pd.DataFrame| R[Runner.fit + Runner.run]
    R -->|DetectorResult| S[ResultsStore]
    S -->|RunResult| DB[("Postgres + TimescaleDB\n(metric_runs, check_runs)")]
    R -->|verdict = fail/warn| I[Incident created]
    I --> N[Notifiers\n(Slack, PD, email)]
    I --> AG[AI Agent]
    AG -->|tool calls| L[Lineage graph]
    AG -->|tool calls| C[Causal DAG]
    AG -->|structured JSON| UI[Web UI incident detail]
```

---

## Key design decisions

### Library isolation

`packages/dqt` must remain importable without FastAPI, Redis, or Postgres. The `MemoryStore` is the default results store. Server-only concepts (auth, tenancy, scheduling) are never imported from the library. This guarantees the library is usable in notebooks, CI pipelines, and Airflow/Dagster tasks without any service infrastructure.

### DuckDB for statistical work

All detectors operate on `pd.DataFrame` samples. When sampling from a warehouse, data is loaded into DuckDB for uniform statistical processing regardless of the upstream engine (BigQuery, Snowflake, Postgres, etc.). This keeps detector code engine-agnostic and allows running the full test suite offline.

### ibis for warehouse portability

Warehouse adapters wrap ibis-framework backends for portable SQL expression building and lazy push-down. For large aggregates (e.g. `COUNT(*)`, `MAX(col)`) the aggregate is executed directly in the warehouse via `adapter.aggregate()`. Sampling falls back to `TABLESAMPLE` where supported, or `LIMIT n` otherwise.

### Single detector contract

Every detector implements `fit(reference: pd.DataFrame) → state` and `score(current: pd.DataFrame, state) → DetectorResult`. There is one canonical implementation per statistical method. The `STAT_SCALES` dict in `_scales.py` is the single source of truth for verdict thresholds — never duplicated in the frontend (generated via `make stats-scales`).

### Honest causal claims

Every reported causal edge carries an E-value (sensitivity to unobserved confounders). Edges with E-value < 1.5 display a "fragile" badge. The AI agent always cites the evidence (detector slug, DAG edge, lineage path) — it never asserts causation without support from the confirmed DAG.

### Cost guards

BigQuery and Snowflake adapters call `dryRun` / `EXPLAIN` before executing queries. If the estimated bytes exceed the source's `max_bytes_per_query` limit (default 50 GB), the query is refused. Every adapter wraps queries in a read-only transaction or uses a read-only role — the library never writes to a warehouse.

### Enum single source of truth

All enums and constants are authored in `shared/config/*.config.json` (severity, check kinds, lifecycle states) or in Python source (`STAT_SCALES` in `_scales.py`, engine configs in `adapters/<engine>/config.py`). Both TypeScript and Python consumers use generated files. Generated files are git-ignored; never edit them manually.
