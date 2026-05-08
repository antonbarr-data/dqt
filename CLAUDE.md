NB This file is copied to CLAUDE.md and .cursor/rules/overview.mdc

# App overview
- **Product**: `dqt` — open-source data quality, observability, semantic, and causality library + service. Watches dbt-built warehouses (and any SQL warehouse) for statistical drift, anomalies, silent regressions, and explains *why* metrics moved.
- **Positioning**: pip-installable Python library at the core (open-source, MIT). `apps/server` (FastAPI) exposes it as a multi-tenant service. `apps/web` (Next.js) is the power-user UI. Library is usable standalone in notebooks, CI pipelines, and Airflow/Dagster/Prefect tasks without the server.
- **Scope vs. peers**: superset of Great Expectations (declarative checks), Soda (SodaCL rules), and Elementary (dbt artifact ingestion). dqt additionally ships a full statistical/ML detector library, a semantic layer, column-level lineage, causal-discovery DAGs, an HITL review loop, an AI agent for incident explanation, and an on-call/incident manager. See "Algorithms catalog" below.
- **Tenants**: Multi-tenant SaaS deployment of the server. Library itself is single-tenant (one workspace per process). Library API is tenant-agnostic; server adds the tenant layer.
- **Architecture**: uv-managed Python monorepo. `packages/dqt` is the library (zero web deps). `apps/server` is a FastAPI service that imports the library. `apps/web` is a Next.js 14 App Router frontend. Optional `apps/worker` runs scheduled checks via arq (Redis-backed task queue).
- **Key data model**: `Source` (warehouse connection) → `Dataset` (table/view) → `Column` → `Check` (statistical or rule) → `Run` (one execution) → `Incident` (when a Run breaches threshold). On top: `Metric` (semantic-layer definition) → `MetricDriverEdge` (causal edge in the driver-tree DAG) → `MetricRun` (snapshot of metric value over time).
- **Tech stack**: Python 3.12+, FastAPI, SQLAlchemy 2.x async, Alembic, Pydantic v2, arq, ibis-framework (warehouse portability), sqlglot (SQL parsing for lineage), DuckDB (embedded analytics on samples), Postgres + TimescaleDB (results store), pgvector (semantic embeddings), Redis (cache + arq broker). Frontend: Next.js 14 App Router, Tailwind, shadcn/ui, lucide-react, zustand, React Query. Anthropic Claude SDK for the AI agent.
- **Brand**: `dqt` wordmark — lowercase, JetBrains Mono weight 300, `-0.05em` tracking. Zero border-radius everywhere. Sharp corners. Dense power-user UI. Dark default, light supported. See "UI design system" below — values are intentional and ported from the dqt design handoff.
- **Third-party services**: Anthropic Claude API (agent + plain-English explanation), optional PagerDuty / Opsgenie / Slack / Microsoft Teams for on-call routing, optional Sentry for error tracking. dbt Cloud and Elementary artifact ingestion are first-class.

# General
- Be concise and direct with user communication.
- Use TodoWrite for complex multi-step tasks.
- Challenge user requests when better approaches exist — especially around statistical correctness. If a check is going to produce false positives at scale (e.g. raw Z-score on heavy-tailed data), say so and propose the right method.
- If not sure just ask the user.
- User is your helper — if you need to see how the UI looks or you need the user to check console/backend logs just ask.
- No workarounds or fallbacks in code ever! Everything must work through one preferred path. Same applies to algorithms — one canonical implementation per method, never two.
- Avoid duplicate code — create common helper methods wherever appropriate. Especially: every detector returns the same `DetectorResult` shape; every adapter implements the same `WarehouseAdapter` protocol.
- Aim to split source files >1,000 lines.
- Very concise comments in code. For statistical methods, link the canonical paper/reference at the top of the file in a single line — that's the spec, the code is the implementation.
- After changes offer the user to run unit tests, git commit and push — but don't commit without specific permission.
- Don't create a dedicated documentation file for each fix/fixture, only for substantial architecture issues and after checking with the user. Algorithm reference is the exception — every detector gets a one-paragraph entry in `docs/algorithms/`.
- After writing any front-end code check `pnpm build` and fix errors and warnings.
- Library code (`packages/dqt/`) must remain importable without the server, without Redis, and without Postgres. The library degrades to in-memory results store if no Postgres is configured. **This is a hard rule — never import server-only modules from the library.**

# Architecture

## Monorepo layout
- **Tooling**: `uv` workspace at the repo root manages all Python packages. `pnpm` workspace manages `apps/web` and `apps/web-shared`. Single `Makefile` orchestrates both.
- **Packages**:
  - `packages/dqt/` — the open-source library. Everything publishable to PyPI. **No FastAPI, no web concepts, no auth.** Pure Python.
  - `packages/dqt-cli/` — `dqt` command-line tool (init, run, fit-baselines, explain). Wraps the library.
  - `packages/dqt-types/` — generated TypeScript types from the library's Pydantic models. Git-ignored, regenerated by `make types`.
- **Apps**:
  - `apps/server/` — FastAPI service. Imports `dqt` library. Adds auth, multi-tenancy, REST/WebSocket APIs, scheduling.
  - `apps/worker/` — arq worker for scheduled check runs and the AI agent loop.
  - `apps/web/` — Next.js 14 App Router frontend. Imports `dqt-types` for API contracts.
- **Open-source boundary**: `packages/*` is MIT-licensed and published to PyPI. `apps/*` is the reference deployment, also MIT, but not published.

## Database
- **Primary OLTP**: PostgreSQL 16+ with **TimescaleDB** extension for the time-series tables (`metric_runs`, `check_runs`, `incidents_history`) and **pgvector** for semantic embeddings (column descriptions, metric descriptions, incident summaries).
- **Embedded analytics**: **DuckDB** is the library's in-process analytics engine. When dqt samples rows from a warehouse it loads them into DuckDB and runs all detectors there — keeps detector code uniform across all 5+ warehouse engines.
- Schema files live at `packages/dqt/src/dqt/store/sql/schema_*.sql` and `apps/server/src/dqt_server/db/schema_*.sql`. These must match the current database schema.
- Simple additive changes use **migra** for diff-driven migrations. Anything destructive or order-sensitive requires an **alembic** script. Never change the DB schema directly — keep all envs in sync via migra or alembic only.
- Library results store is pluggable: `MemoryStore` (default, for notebooks), `PostgresStore` (with TimescaleDB), or any custom backend implementing `ResultsStore`. Server pins it to `PostgresStore`.

## Warehouse adapters
- **Supported engines**: PostgreSQL, MySQL, ClickHouse, BigQuery, Snowflake, Redshift, Databricks SQL, DuckDB, Trino/Presto. (The handoff specifies the first 5 as visual + connection-wizard targets — we ship adapters for the rest because they share the same SQL/ibis backend with near-zero marginal cost.)
- **Abstraction**: `dqt.adapters.WarehouseAdapter` protocol. Each adapter wraps an `ibis-framework` backend, implements `list_schemas`, `list_tables`, `describe_columns`, `sample`, `aggregate`, `info_schema_meta`, `health_check`, `cost_estimate`, `cancel`.
- **Why ibis**: portable expressions across engines, lazy execution, push-down to the warehouse for big aggregates, fall back to DuckDB for stat work on samples.
- **Health check protocol** (matches the wizard's 6 steps in the design): TCP reach → auth → info_schema read → sample SELECT → latency probe → clock skew. Each step returns `{name, status, latency_ms, detail}`.
- **Engine-specific config**: `packages/dqt/src/dqt/adapters/<engine>/config.py` defines the exact fields shown in the connection wizard. **Field set must match `apps/web/src/components/connections/engines.ts` 1:1** — that file is generated from the Python config.
- **Sampling rules**: never read full tables for stats. Default sample is reservoir-sample of 100k rows or `LIMIT 100000 TABLESAMPLE` where supported. Detector contract guarantees correctness on samples that size; bigger samples are configurable per check.
- **Cost guard**: BigQuery and Snowflake adapters call `dryRun` / `EXPLAIN` first, refuse to run if estimated bytes exceed the source's `max_bytes_per_query` config (default 50 GB).
- **Read-only enforcement**: every adapter wraps queries in a read-only transaction or uses a connection user with read-only role. Never write to warehouse.

## Algorithms catalog (the heart of the library)
Single canonical implementation per method. Each lives at `packages/dqt/src/dqt/algorithms/<group>/<method>.py`, exports a class implementing `Detector` with `fit(reference) → state`, `score(current, state) → DetectorResult`, and a registered slug.

Method coverage — superset of GX, Soda, and Elementary, plus the algorithms reference document:

- **Distribution diagnostics**: Shapiro-Wilk, Anderson-Darling, Lilliefors, KS (1-sample for normality, 2-sample for drift), Hartigan's dip, skewness, kurtosis, ADF, KPSS, Ljung-Box.
- **Univariate outliers**: Z-score, modified Z-score (MAD), MAD, double MAD, IQR/Tukey fences, adjusted boxplot (medcouple), Grubbs', generalized ESD (Rosner), quantile-based.
- **Multivariate outliers**: Mahalanobis (with MCD for robust covariance), Isolation Forest, LOF, DBSCAN, One-Class SVM, HBOS, COPOD, ECOD (default for high-dim tabular), ABOD, autoencoder (optional, behind extra `dqt[deep]`), PCA reconstruction error, Random Cut Forest, GMM+EM.
- **Time series anomalies**: STL, Holt-Winters, Prophet (optional `dqt[forecast]`), seasonal hybrid ESD, Matrix Profile (STUMPY), CUSUM, Page-Hinkley, BOCPD.
- **Drift**: PSI, KL divergence, Jensen-Shannon, Wasserstein-1 (earth-mover), MMD, KS-for-drift, chi-square (categorical), ADWIN, DDM/EDDM.
- **Causal**: Granger, Transfer Entropy, Convergent Cross Mapping (CCM), PCMCI/PCMCI+ (via tigramite, optional `dqt[causal]`), PC, FCI, GES, NOTEARS/DAGMA, LiNGAM, do-calculus identification (DoWhy), sensitivity analysis (E-values, Rosenbaum bounds).
- **Information theory & associations**: Cramér's V, Theil's U, mutual information.
- **Pattern & specialized**: Benford's Law, SHAP attribution, Bayesian networks (pgmpy), functional dependency mining (Tane).
- **Dimensionality reduction**: PCA, robust PCA.
- **Ensembling**: score normalization (unification), average / max / AOM / MOA combinations, stacking, diversity measures.
- **Calibration**: empirical-CDF calibration, Platt scaling, isotonic regression, bootstrap CIs.
- **Active learning (HITL)**: uncertainty sampling, query-by-committee.
- **Semantic layer support**: sentence-transformers embeddings, Levenshtein, Jaro-Winkler, LSH (datasketch).

Compatibility shims (so users can adopt dqt without rewriting): `dqt.compat.gx` runs a Great Expectations `ExpectationSuite` through dqt's runner; `dqt.compat.soda` parses SodaCL YAML into native dqt checks; `dqt.compat.elementary` ingests Elementary's dbt artifacts and produces dqt Datasets/Sources.

Every detector also publishes a `STAT_SCALE` entry — `(metric_slug, max, warn_threshold, fail_threshold, direction, plain_english_label, hint)`. The frontend's `<StatGauge>` reads this to render the verdict band consistently. Single source of truth: `packages/dqt/src/dqt/algorithms/_scales.py`. **Never duplicate scales on the frontend.** Generated to TS via `make stats-scales`.

## Checks (declarative tests)
- A `Check` is a YAML or Python definition that binds a detector to a target (column/table/metric) with parameters and a baseline reference.
- File format is a strict superset of SodaCL with native dbt-style tests included. See `packages/dqt/src/dqt/checks/schema/check.schema.json` for the JSON Schema.
- Auto-baselining: when a Check is created, dqt fits the reference window automatically (default last 14d). Re-fits on schedule or manual trigger ("Re-fit baselines" in the UI).
- Plain-English authoring: the UI's natural-language input compiles to YAML via the agent. The YAML is always the source of truth — the natural-language input is never executed directly.
- Test taxonomy (mirrors UI tabs): `Auto-baselined`, `Distribution`, `Time series`, `Outliers`, `Dependencies`, `Schema`, `Basic`. Each tab maps to a `group` field on the detector registry.

## Lineage
- **Column-level lineage** parsed from warehouse SQL via **sqlglot**. Plus dbt manifest ingestion for projects that have one. Plus optional OpenLineage event ingestion.
- Storage: edge list in `lineage_edges` (upstream_dataset, upstream_column, downstream_dataset, downstream_column, transform_kind, confidence). DAG views materialized through Postgres recursive CTEs.
- Coverage overlay: each lineage node carries `% of columns watched` for the lineage screen's heatmap.
- Failure-blast-radius: from any incident, `lineage.downstream_impact(incident)` returns the affected downstream nodes for the "causal trace" panel on the incident detail screen.

## Semantic layer
- **Metric definitions** as YAML contracts: `id`, `name`, `kind` (sum / count / ratio / model), `source` (column expression or other-metric expression), `dimensions[]`, `owner`, `description`, `unit`. Compatible with dbt's semantic layer where possible (we read `semantic_models.yml` directly).
- Every metric defined here is automatically watched by four checks: **Shape change** (KS), **Level shift** (Wasserstein-1), **Spike** (STL residual z-score), **Trend break** (BOCPD). Configurable per metric.
- Tables/columns/metrics also carry **descriptions** (markdown) and **relationships** (FK-style edges and equivalence relations). Embeddings on descriptions power semantic search and the agent's grounding.
- Metric values are stored as a Timescale hypertable (`metric_runs`) — that's the substrate the causality layer learns on.

## Causality layer (driver-tree DAG)
- **Goal**: an automatically-discovered directed graph of metric→metric influence, with edge weights, lags, and uncertainty.
- **Discovery pipeline**: PCMCI+ on the metric panel → prune by stability selection across bootstrap resamples → annotate edges with Transfer Entropy magnitudes and Granger F-statistics → present as a DAG.
- **Refresh cadence**: weekly by default, on-demand from the Causality screen.
- **HITL gate**: discovered DAG is **proposed**, not committed. Owners review/edit/confirm in the Causality screen; only confirmed edges enter the production DAG used for attribution. The HITL queue (uncertainty sampling) prioritizes edges with the lowest stability score.
- **Attribution at incident time**: Shapley value decomposition over the confirmed DAG explains a metric's current move as a fair-share split across upstream parents. This is what the incident detail's "Causal trace" timeline renders.
- **Honest causal claims**: every reported edge carries an E-value (sensitivity to unobserved confounders). UI shows a "fragile" badge on edges with E-value < 1.5.
- **Pearl-style do-calculus** for hypotheticals ("what if conversion held flat?") — used by the AI agent when the user asks counterfactual questions.

## AI agent
- **Provider**: Anthropic Claude (current model in `agent.config.model` — keep updated). Library exposes a generic `LLMProvider` protocol; Claude is the reference impl. Server defaults to Anthropic.
- **Loop**: triggered by (a) new incident fired, (b) user asking "explain this", (c) scheduled metric review (daily for warn metrics, hourly for fail). The agent reasons over: incident statistical evidence, the metric's confirmed causal DAG, lineage upstreams, semantic descriptions, recent changepoints, and prior similar incidents.
- **The Why**: agent operates on Pearl's ladder of causation explicitly. Level 1 (association) → describe what changed. Level 2 (intervention) → query the causal DAG for likely drivers via do-calculus identification. Level 3 (counterfactual) → answer "would this have happened anyway?" using DoWhy refuters. Each level is a separate tool call so reasoning is auditable. **Output always cites the evidence (which detector, which DAG edge, which lineage path) — never an unsupported assertion.**
- **Tools available to the agent**: `query_warehouse(sql)` (read-only, sandboxed), `run_detector(slug, params)`, `walk_lineage(node, direction)`, `get_dag_attribution(metric, t)`, `do_calculus(metric, intervention)`, `search_incidents(query)`, `get_metric_definition(id)`. All defined in `packages/dqt/src/dqt/agent/tools.py`.
- **Output format**: structured JSON with `{plain_english, evidence[], confidence, follow_up_questions[]}`. Frontend renders the plain-English part with citations linking to the evidence.
- **Cost control**: per-tenant token budget, configurable. Agent caches reasoning by `(incident_id, evidence_hash)` to avoid re-running the same chain.
- **No hallucinated SQL**: warehouse queries the agent generates are validated against the lineage graph before execution and capped at the source's cost limit.

## HITL review
- **Queue**: a single inbox of items needing human judgment — proposed causal edges, uncertain incident classifications, ambiguous semantic mappings, suggested checks from the auto-baseliner.
- **Sampling strategy**: uncertainty sampling by default. Switchable to query-by-committee when multiple detectors disagree.
- **Outcome**: every reviewed item produces a labeled training example written back to `hitl_labels`. The auto-baseliner and the causality layer both consume this — the system gets steadily better at the things this user cares about.
- **No silent overrides**: a confirmed-then-later-reverted decision is logged with the reviewer, timestamp, and reason.

## Governance
- **Catalog**: every Source/Dataset/Column/Metric carries `owner`, `domain`, `tags[]`, `classification` (public / internal / confidential / restricted), `pii` flag, `freshness_sla`, `description`. Catalog backed by the same Postgres store; queryable via REST and via the Cmd-K palette.
- **Policies**: declarative YAML at `governance/policies/*.yaml`. Examples: "no PII column may be sampled into the agent's context", "freshness SLA for `fct_*` is 1h", "all metrics in domain=finance require an owner". Enforced at runtime by `dqt.governance.PolicyEngine` — every detector run, every agent tool call, every API call passes through it.
- **Audit log**: append-only `audit_log` table. Records actor, action, target, before/after, IP, user-agent. Exposed in UI under Settings → Audit.
- **Access control**: row-level security in Postgres scoped by `tenant_id` plus optional dataset-level ACLs.

## Incidents & on-call
- **Incident lifecycle**: `open` → `investigating` → `resolved` → `closed`. Plus `snoozed` and `auto_resolved` states. Severity: `fail` / `warn`. State transitions auditable.
- **Schedules**: `oncall_schedules` table with rotations. UI shows current on-call in the sidebar footer (matches design — "Jamie Lin · on-call · ends 18:30").
- **Routing rules**: YAML at `oncall/routes.yaml`. Match by `(domain, dataset_pattern, severity, time_of_day)`, route to schedule + escalation policy. Mirrors PagerDuty's mental model but native — PagerDuty/Opsgenie are integrations, not requirements.
- **Tasks**: each incident has child `tasks` (acknowledge, investigate, mitigate, write postmortem). Tasks are assignable, have due dates, can be completed in the UI or via Slack/Teams reaction.
- **Channels**: Slack/Teams/email/SMS/PagerDuty/Opsgenie/webhook. All implemented as `Notifier` plugins. Tenant configures which to enable.
- **Auto-resolve**: when the same check passes for `auto_resolve_after` consecutive runs (default 3) the incident closes automatically with a note.
- **Postmortems**: optional template-driven postmortem doc generated by the agent from the incident's evidence + activity log. Editable.

## Enums and config
- **Single source of truth**: All enums and constants live in JSON files at `shared/config/*.config.json` and are auto-generated for frontend/backend.
- **Statistical scales** (`STAT_SCALES`): generated from `packages/dqt/src/dqt/algorithms/_scales.py` via `make stats-scales` — Python is authoritative because the library is the source of stat truth.
- **Engine catalog** (`ENGINES`): generated from `packages/dqt/src/dqt/adapters/<engine>/config.py` via `make engines` — Python is authoritative because the library is what actually connects.
- **Other enums** (severity, lifecycle states, check kinds, etc.): authored in JSON, generated to both sides.
- **Value not label** in DB. Always store the canonical slug (e.g. `ks`, not `Kolmogorov–Smirnov`). UI looks up the label from the generated dictionary.
- **Never hardcode enums**. Import from `dqt_types` (TS) or the generated module (Python). Database CHECK constraints reference the JSON file in a comment.
- **Generated files are git-ignored.** Never edit or commit them.

## Backend endpoints (FastAPI)
- **Versioned**: all under `/api/v1`. URL-based versioning.
- **REST conventions**: GET/POST/PUT/PATCH/DELETE. Plural resources. Sub-resources for relationships. Structured error envelope (see "Error handling").
- **Pydantic v2 everywhere**: request/response models are Pydantic. The library's domain models are also Pydantic so the same models flow library → server → wire.
- **OpenAPI is the contract**: the spec at `/openapi.json` is generated from Pydantic. `dqt-types` regenerates TS types from this. **Frontend never imports custom types for API shapes.**
- **WebSocket** at `/api/v1/ws` for live incident feed and check-run progress. Auth via the same JWT.
- **Rate limiting**: per-tenant + per-IP via SlowAPI on Redis. Stricter limits on agent endpoints (cost guard).

## Authentication & Authorization
- **Library**: no auth. Pure functions. Caller is responsible.
- **Server**: JWT via `fastapi-users` (or equivalent). User identity in `sub` claim, tenant in `tenant` claim, role in `role` claim.
- **Context**: `request.state.user_id`, `request.state.tenant_id`, `request.state.role` populated by middleware `apps/server/src/dqt_server/middleware/auth.py`.
- **Roles**: `viewer` / `editor` / `admin` / `oncall` / `sysadmin`. Permissions in `apps/server/src/dqt_server/auth/permissions.py`.
- **Sysadmin emulation**: sysadmins can act-as another user. Logged in audit log with both identities.
- **Testing**: dependency-override `get_current_user` with a fixture user. Don't patch middleware.
- **Multi-tenant scoping**: all queries pass through `TenantScopedRepository` which injects `tenant_id` automatically. RLS in Postgres as defense-in-depth.

## Error handling
- **Backend format**: structured JSON `{"error": {"code": "ERROR_CODE", "message": "...", "details": {...}, "trace_id": "..."}}`.
- **FastAPI exception handlers**: one global handler maps Pydantic ValidationError, library `DqtError` subclasses, SQLAlchemy errors, and `HTTPException` to the envelope.
- **Library error hierarchy**: `DqtError` → `AdapterError`, `DetectorError`, `CheckDefinitionError`, `LineageError`, `CausalityError`, `GovernancePolicyViolation`, `AgentError`. All carry `code` and `details`.
- **Frontend**: `handleApiError(error, form)` from `apps/web/src/lib/error-handling.ts`. Toast via `sonner`. Field errors mapped to `react-hook-form` automatically.
- **Logging**: every error logged with `trace_id` (W3C traceparent), tenant, user, request path. **Never swallow exceptions.** User must always know when there's been a technical error.

## Logging
- **Library**: `structlog` with JSON output. Logger acquired via `dqt.utils.logging.get_logger(__name__)`. **Never** `logging.getLogger(__name__)` directly.
- **Server**: same `structlog` config + request-scoped context (trace_id, tenant_id, user_id) injected via middleware.
- **Levels**: INFO root, DEBUG for `dqt.algorithms` in dev, WARNING for `sqlalchemy.engine` and `httpx`.
- **Control**: env vars `DQT_LOG_LEVEL`, `DQT_LOG_LEVEL_<MODULE>`. CLI tool `dqt logs --tail`.
- **PII redaction**: log filters redact values from columns marked `pii=true` in the catalog. Statistical results are safe (they're aggregates).

## API patterns
- **REST** under `/api/v1`.
- **Versioning**: URL-based.
- **Response shape**: `{data, meta}` for collections, raw object for singletons. Errors as above.
- **Routers** organised by module under `apps/server/src/dqt_server/api/v1/<module>/routes.py`.
- **Tenant scoping**: automatic via dependency.

## Repository pattern
- **Base class**: `BaseRepository` in `apps/server/src/dqt_server/repositories/base.py`.
- **Features**: tenant-aware operations, soft deletes, optimistic concurrency via `version` column, pagination (cursor-based for large lists, offset for small), TimescaleDB-aware (uses `time_bucket` for time-series queries).
- **Library equivalent**: `dqt.store.Store` interface — implemented by `MemoryStore` and `PostgresStore`. Server's repositories wrap `PostgresStore` with the auth layer.
- **Examples**: `SourceRepository`, `DatasetRepository`, `CheckRepository`, `IncidentRepository`, `MetricRepository`, `LineageRepository`.

## Cloud deployment (reference)
- **Backend**: containerised, runs on any container platform (Cloud Run / ECS / Fly / Kubernetes). Reference deployment is Google Cloud Run, 4Gi/2CPU, port 8080.
- **Worker**: same image, different entrypoint (`arq dqt_server.worker.WorkerSettings`). Scales independently.
- **Database**: Cloud SQL Postgres 16 with TimescaleDB and pgvector extensions enabled, 10 pool / 40 overflow.
- **Cache/queue**: Memorystore Redis (or any managed Redis). VPC connector for private access.
- **Frontend**: Next.js standalone output, served from Cloud Run or a static-friendly target. Static assets via CDN.
- **Secrets**: Secret Manager prefix `dqt-*` (database-url, jwt-signing-key, anthropic-api-key, warehouse-credentials-{id}).
- **CI/CD**: GitHub Actions — install → lint → typecheck → unit + integration → build images → migrate → deploy. Library publishes to PyPI on tags matching `dqt-v*`.
- **Setup**: `./setup/cloud/google-cloud-setup.sh` (initial) and `./deployment/cloud/deploy.sh` (manual rollouts).
- **Edge**: load balancer routes `/api/*` and `/ws/*` → server, everything else → frontend.

## Local deployment
- **Architecture**: server/worker/frontend native; Postgres/Redis/MailHog in Docker.
- **Ports**: server 8000, worker (no port), frontend 3000, Postgres 5434 (main), 5435 (unit tests), 5436 (integration tests), 5437 (e2e), Redis 6379, MailHog 8025, Adminer 8081.
- **Config**: `local.env` (git-tracked, non-secrets), `.env` (git-ignored, secrets only).
- **Bring-up**: `./run_local/start.sh` starts containers, runs migrations, seeds demo data (synthetic warehouse with `fct_orders`, `fct_sessions`, etc. matching the design's mock data).
- **Server modes**: `uvicorn dqt_server.main:app --reload` (dev), `./run_local/start-server-prod.sh` (Gunicorn with uvicorn workers, production-like).
- **Hot reload**: frontend and backend reload automatically — don't restart them.
- **Demo warehouse**: `dqt demo seed` populates a local Postgres with realistic data so every screen has something to show.

## Testing
- **Tools**: pytest (Python unit + integration), Vitest (frontend unit), Playwright (E2E).
- **Database isolation**: each test type has a dedicated Postgres on a unique port (unit:5435, integration:5436, e2e:5437). Unit tests get 4 parallel workers (5435, 5438–5440) with isolated databases, in-memory tablespaces.
- **Library-only tests**: `packages/dqt/tests/` — must run without Postgres, without Redis, without network. Use `MemoryStore` and offline fixture data. CI gates on these passing in <60s.
- **Algorithm tests**: every detector has a `test_<method>.py` with: known-answer tests against a textbook example, behaviour tests on synthetic distributions (drift / no-drift), property tests via `hypothesis` for numerical stability, golden-file tests for `STAT_SCALE` verdicts.
- **Adapter tests**: `packages/dqt/tests/adapters/` runs against the real engine via testcontainers (Postgres, MySQL, ClickHouse) or against a recorded fixture (BigQuery, Snowflake — recorded with `vcrpy`).
- **Server tests**: `apps/server/tests/` — unit (mock the library) and integration (real library + testcontainers Postgres).
- **Markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.adapter`, `@pytest.mark.slow`.
- **Auth in server tests**: dependency-override `get_current_user`, never patch middleware.
- **Commands**: `./tests/run_unit_tests.sh`, `./tests/run_integration_tests.sh`, `./tests/run_adapter_tests.sh`, `./tests/run_e2e_tests.sh`, `./tests/run_all_tests.sh`. Use `--skip-db-reset --skip-schema-gen` for fast iteration.
- **Test data**: realistic fixtures in `tests/data/` organised by type (`tests/data/warehouses/`, `tests/data/dbt_artifacts/`, `tests/data/golden_outputs/`).
- **Best practices**: test the real library in integration tests — don't mock detectors. Use pytest style (functions + fixtures), not unittest.

## i18n
- ALL user-facing strings use i18n. ALL user-facing numbers, dates, durations use locale-aware components.
- **Frontend**: `next-intl`, translations in `apps/web/messages/[lang]/[module].json`.
- **Namespaces**: per route group (`overview`, `datasets`, `incidents`, `metrics`, `causality`, `tests`, `connections`, `settings`) plus `common` for reusable strings.
- **Usage**: `const t = useTranslations('moduleName'); t('key.path')`.
- **Backend**: `Accept-Language` honoured for error messages and emails. `EmailTranslationService` for outbound notifications. User's `preferred_language` stored on the profile.
- **Generated content from the agent**: the AI agent always responds in the user's preferred language. Plain-English labels for stat methods are translated; method names (e.g. `KS`, `Wasserstein-1`) are not.
- **Rules**: write English first, AI translates the rest via `pnpm run i18n:translate`. Reuse existing strings. Verify the actual JSON structure before adding keys.
- **Localized components** in `apps/web/src/components/localized/`:
  - `LocalizedNumber` — locale-aware decimal/grouping
  - `LocalizedStatValue` — uses scale's `valueFormat` (e.g. p-values get `.toExponential(2)`)
  - `LocalizedDate` / `LocalizedDateTime` — short/medium/long, 12h/24h
  - `LocalizedDuration` — relative durations ("2m ago", "in 14d")

# UI design system
Ported verbatim from the dqt design handoff. **High fidelity — every value is intentional.** Source: `design_handoff_dqt/`.

## Stack
- Next.js 14 App Router, React Server Components by default, client components only for charts, gauges, and any hover/click state.
- Tailwind CSS, shadcn/ui primitives, lucide-react icons (stroke-width 1.6), `next/font/google` for Inter Tight + JetBrains Mono.

## Tokens
- **Two themes**: dark (default) + light. Toggle persisted in `localStorage`, applied as `data-theme="dark|light"` on `<html>`. Map CSS variables in `app/globals.css` `@layer base { :root { ... } }`, extend Tailwind theme in `tailwind.config.ts`.
- **Colors** — semantic: `accent` `#9DD0B0`, `accent-bg` `rgba(157,208,176,0.10)`, `pass` `#7FB394 / #5A8F70`, `warn` `#D9B566 / #B89540`, `fail` `#E07B6E / #C25D52`, `fail-bg` `rgba(224,123,110,0.07)`. Neutrals: `bg-0..3`, `line / line-2 / line-3`, `fg-0..3` per theme — values in `tokens/globals.css`.
- **Type**: Inter Tight (UI, body, headings, weights 200–600, features `ss01 cv11`); JetBrains Mono (code, identifiers, numeric KPIs, statistical values, weights 300–500, feature `calt 0`). Type scale: `t-display` / `t-h1..3` / `t-body` / `t-small` / `t-micro`. KPI: `kpi-label` (10px, 0.16em uppercase) and `kpi-value` (32px, weight 300, tabular-nums).
- **Spacing**: Tailwind default 4px grid.
- **Radius**: `0` everywhere. Sharp corners.
- **Borders**: 1px, color from `line` tokens.
- **Shadows**: only the status-dot halo (`box-shadow: 0 0 0 2px rgba(...)`). No drop shadows.

## Components
- **shadcn primitives**: Button (with `accent` variant), Badge (pass/warn/fail variants), Card (radius override to 0), Tabs, Dialog, Table, Command (Cmd-K), Tooltip, Sheet, Form/Input/Select/Label, Toast (Sonner).
- **Custom — port verbatim from `source/`**:
  - `<StatGauge metric value label />` — most-reused. Horizontal bar with green/amber/red zones and threshold ticks. Reads `STAT_SCALES` from `lib/stats.ts`.
  - `<StatChip metric value />` — inline compact gauge for table cells.
  - `<InfoTip>` — `(i)` icon + tooltip, exposes the underlying stat method.
  - `<Spark data w h color />` — tiny inline SVG line chart (~60×20).
  - `<TimeSeries data band anomalies changepoints />` — larger time series with confidence band, anomaly markers, changepoint verticals.
  - `<HistDual a b />` — overlapping histograms (current orange, baseline gray).
  - `<CDFPair a b />` — overlapping CDFs with KS supremum point marked.
  - `<KLMatrix metrics matrix />` — symmetric heatmap, masked diagonal.
  - `<CausalDAG nodes edges target onSelect />` — SVG DAG, bezier edges, weight + lag labels, hover highlights upstream/downstream, click-to-select.
  - `<EngineGlyph engine size />` — per-engine SVG glyph (Postgres / MySQL / BigQuery / ClickHouse / Snowflake / Redshift / Databricks / DuckDB / Trino).
- **Layout**: `<AppShell>` — 212px sidebar (collapsible) + topbar (search, Cmd-K trigger, theme toggle, user). Sidebar groups: **Warehouse** (Sources, Datasets, Lineage), **Semantic layer** (Metrics, Causality), **Watch** (Incidents, Tests), **Govern** (Catalog, Policies, Audit), **Team** (On-call, Tasks). Active state = left border + bg tint. Sidebar footer shows current on-call.

## Screens (all under `apps/web/app/(app)/`)
- `/overview` — fleet KPIs, method-coverage cards, datasets table with sparklines, activity feed.
- `/sources` — connections list + Add-Connection wizard (3 steps: Configure → Test & Verify → Choose Tables). Engine cards across the top.
- `/sources/new/[engine]` — wizard step routes (resumable via URL).
- `/datasets` — dataset list with the same table style as overview.
- `/datasets/[id]` — tabs (Overview / Tests / Lineage / Samples) + 2-column body (column list + per-column distribution + StatGauge bank).
- `/lineage` — DAG of warehouse models with test-coverage overlay.
- `/metrics` — semantic layer. 1fr/460px split. Metrics table left, selected metric detail right (YAML, 30d health, "Watching" panel with the four checks).
- `/causality` — directed graph of metric→metric. 1fr/380px split. SVG DAG + KL heatmap on the left; attribution rail (Shapley + agent's plain-English summary) on the right.
- `/incidents` — filter bar + virtualized list. Headline KPIs (open / mean detect / mean resolve / auto-explained).
- `/incidents/[id]` — Headline KPI band → statistical evidence → segment decomposition → causal trace. Right rail: rule definition, activity log, agent explanation, related past incidents.
- `/tests` — tab bar (Auto-baselined / Distribution / Time series / Outliers / Dependencies / Schema / Basic) + catalog list + detail/authoring panel. Plain-English authoring compiles to YAML live preview.
- `/catalog` — searchable catalog of sources, datasets, columns, metrics with classification, owners, tags.
- `/oncall` — schedules, rotations, escalation policies.
- `/tasks` — task board for incident handling, assignable, due dates.
- `/settings` — workspace settings, integrations, audit log.

## Interactions
- **Theme toggle**: persisted, `data-theme` on `<html>`.
- **Cmd+K**: global command palette. Quick nav, dataset search, recent incidents, "explain X" agent shortcut.
- **Wizard navigation**: forward disabled until current step's invariants hold.
- **Hover row → bg-1 tint** on tables. Click navigates.
- **Status dot**: 8px circle + 2px halo at 18–22% opacity.
- **Animations**: 220ms `fadeIn` on screen mount (slide-in from 2px). 240ms ease-out on bar widths. Otherwise no motion.
- **Tooltips**: 6px gap above target, `bg-1` surface, 1px border.

## State management
- Server-render where possible. Client components for charts, gauges, hover/click state.
- **Theme**: zustand, persisted.
- **Cmd-K open**: component-local.
- **Wizard**: URL params for resumability.
- **Selected column / metric / DAG node**: URL search params (e.g. `?col=order_total`).
- **Server data**: React Query (TanStack Query) with the OpenAPI-typed client.

## Frontend module folder pattern
`apps/web/src/modules/[module_name]/`
- `components/` — module-specific React components
- `hooks/` — custom hooks
- `services/` — API service layer (calls into the generated OpenAPI client)
- `__tests__/` — Vitest tests

# Library module structure
`packages/dqt/src/dqt/[module]/`
- `__init__.py` — public API
- `models.py` — Pydantic domain models
- `<service>.py` — implementation files
- `tests/` — pytest tests (note: tests live next to source, not in a separate top-level dir, because the library is published)

# Server module structure
`apps/server/src/dqt_server/[module]/`
- `api/` — FastAPI routers
- `services/` — business logic on top of the library
- `repositories/` — data access
- `schemas/` — request/response Pydantic models
- `tests/` — pytest tests

# Library main modules
- `dqt.adapters` — warehouse connectors (postgres, mysql, clickhouse, bigquery, snowflake, redshift, databricks, duckdb, trino)
- `dqt.algorithms` — all detectors (distribution, outliers_uni, outliers_multi, timeseries, drift, causal, info, pattern, dimred, ensemble, calibration, hitl)
- `dqt.checks` — declarative check definitions, YAML loader, runner
- `dqt.lineage` — sqlglot-based column lineage, dbt manifest ingest, OpenLineage ingest
- `dqt.semantic` — metric/dimension definitions, descriptions, embeddings
- `dqt.causality` — discovery (PCMCI+, PC, etc.), DAG store, attribution (Shapley), do-calculus
- `dqt.governance` — catalog, policies, audit log, classification
- `dqt.hitl` — review queue, label store, active-learning samplers
- `dqt.agent` — LLMProvider protocol, Anthropic impl, tools, reasoning loops
- `dqt.runner` — check execution engine, scheduling primitives
- `dqt.store` — results store interface (Memory, Postgres)
- `dqt.compat` — GX, Soda, Elementary compatibility shims

# Server main modules
- `dqt_server.auth` — JWT, users, roles, permissions
- `dqt_server.tenants` — workspace management
- `dqt_server.sources` — connection CRUD + wizard backend
- `dqt_server.datasets` — dataset metadata, samples
- `dqt_server.checks` — check CRUD, on-demand runs
- `dqt_server.incidents` — incident lifecycle, comments, postmortems
- `dqt_server.metrics` — semantic layer CRUD
- `dqt_server.causality` — DAG management, HITL review endpoints
- `dqt_server.lineage` — lineage queries
- `dqt_server.governance` — catalog, policies, audit
- `dqt_server.oncall` — schedules, escalations, notifications
- `dqt_server.tasks` — task management
- `dqt_server.agent` — agent invocation endpoints (sync + streaming)
- `dqt_server.notifications` — Slack/Teams/email/PagerDuty/Opsgenie/webhook notifiers
- `dqt_server.workers` — arq tasks (scheduled check runs, agent loop, baseliner)

# Folders
- `packages/` — Python packages (library, CLI, types)
- `apps/` — runnable apps (server, worker, web)
- `shared/config/` — JSON enums + constants (single source of truth)
- `shared/schemas/` — JSON Schema files for declarative artifacts (checks, metrics, policies, oncall routes)
- `shared/generated/` — generated TS + Python from schemas + scales + engines (git-ignored)
- `docs/` — documentation
  - `docs/algorithms/` — one-paragraph entry per detector with the canonical reference
  - `docs/architecture/` — substantial architecture docs only
  - `docs/governance/` — policy authoring guide
- `examples/` — runnable examples for the library (notebooks + scripts)
- `tmp/` — put any temporary script here and delete it when done.
- `reference_data/` — seed data (synthetic warehouse, demo dbt project)
- `setup/` — scripts for creating a new environment

# Important files
- `packages/dqt/src/dqt/algorithms/_scales.py` — `STAT_SCALES` source of truth
- `packages/dqt/src/dqt/checks/schema/check.schema.json` — check definition schema
- `shared/config/severity.config.json` — incident severity enum
- `shared/config/check_kinds.config.json` — check kind taxonomy
- `apps/server/src/dqt_server/main.py` — FastAPI entrypoint
- `apps/web/src/app/(app)/layout.tsx` — AppShell

# Further rules files

Before any task must read the most relevant rules and guidelines:
- `.cursor/rules/general-rules.mdc` — Core developer preferences and philosophy
- `.cursor/rules/project-overview.mdc` — Project context and architecture
- `.cursor/rules/library-vs-server.mdc` — The hard boundary between library and server code
- `.cursor/rules/algorithms.mdc` — Detector contract, STAT_SCALES, statistical correctness rules
- `.cursor/rules/adapters.mdc` — Warehouse adapter contract, sampling rules, cost guards, read-only enforcement
- `.cursor/rules/checks.mdc` — Check YAML format, baselining, SodaCL/dbt compatibility
- `.cursor/rules/lineage.mdc` — Column-level lineage, sqlglot patterns, dbt manifest ingest
- `.cursor/rules/semantic.mdc` — Metric definition format, dbt semantic-layer compatibility
- `.cursor/rules/causality.mdc` — Discovery pipeline, HITL gate, Shapley attribution, do-calculus
- `.cursor/rules/agent.mdc` — Agent loop, ladder of causation, tool contract, citation requirement, cost guard
- `.cursor/rules/governance.mdc` — Catalog, policies, audit log, classification
- `.cursor/rules/hitl.mdc` — Review queue, sampling strategies, label store
- `.cursor/rules/incidents-oncall.mdc` — Incident lifecycle, schedules, routing, notifiers, postmortems
- `.cursor/rules/backend-and-python.mdc` — Python/FastAPI patterns, async, Pydantic, SQLAlchemy 2.x async
- `.cursor/rules/frontend-architecture.mdc` — Next.js App Router, RSC, Tailwind, shadcn/ui, React Query
- `.cursor/rules/modules-and-folders-structure.mdc` — Project organisation
- `.cursor/rules/database.mdc` — Schema, migrations (migra/alembic), TimescaleDB, pgvector, RLS
- `.cursor/rules/config_and_enums.mdc` — Configuration and enum management, code generation
- `.cursor/rules/data_model_and_repositories.mdc` — Data layer, BaseRepository, library Store interface
- `.cursor/rules/ui-design-principles.mdc` — UI/UX design standards, density, sharpness
- `.cursor/rules/ui-tokens.mdc` — Colors, type, spacing, borders, shadows
- `.cursor/rules/ui-charts.mdc` — Custom SVG charts (StatGauge, Spark, TimeSeries, HistDual, CDFPair, KLMatrix, CausalDAG)
- `.cursor/rules/ui-forms.mdc` — Form component patterns (react-hook-form + zod)
- `.cursor/rules/ui-list-pages.mdc` — List and table patterns
- `.cursor/rules/ui-page-headers.mdc` — Page header patterns
- `.cursor/rules/ui-view-page.mdc` — Detail page patterns
- `.cursor/rules/design.mdc` — Design system guidelines
- `.cursor/rules/testing.mdc` — Testing standards (library / server / e2e split)
- `.cursor/rules/error-handling.mdc` — Error handling patterns, library exception hierarchy
- `.cursor/rules/logging.mdc` — Logging standards, structlog, PII redaction
- `.cursor/rules/local-deployment.mdc` — Local development setup
- `.cursor/rules/cloud-deployment.mdc` — Cloud deployment procedures
- `.cursor/rules/github-actions.mdc` — CI/CD pipeline rules
- `.cursor/rules/i18n.mdc` — Internationalisation guidelines
- `.cursor/rules/schemas.mdc` — Schema definitions and validation
- `.cursor/rules/glossary.mdc` — Project terminology (plain-English ↔ stat method mapping; lineage/causal/governance terms)
- `.cursor/rules/authentication_and_authorization.mdc` — Authorization, authentication, sessions, sysadmin privileges
- `.cursor/rules/open-source.mdc` — Library publishing rules: no server imports, semver discipline, deprecation policy, public API stability
