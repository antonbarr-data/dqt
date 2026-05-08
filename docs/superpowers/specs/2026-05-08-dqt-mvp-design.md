# dqt MVP Design

**Date:** 2026-05-08  
**Approach:** A — Library-first, build up  
**Status:** Approved

---

## 1. Overview & Scope

Build a full working MVP of dqt: a pip-installable Python library at the core, a FastAPI multi-tenant service on top, and a Next.js frontend with four fully working screens. `make dev` brings up the entire stack; `dqt demo seed` populates realistic data so every screen has something to show.

### What is in the MVP

| Layer | Package | Notes |
|---|---|---|
| Library | `packages/dqt` | Real implementation — adapters, algorithms, checks, runner, store |
| CLI | `packages/dqt-cli` | Minimal: `dqt demo seed`, `dqt run`, `dqt health-check` |
| Server | `apps/server` | Real: auth, sources, datasets, checks, incidents, agent (basic) |
| Worker | `apps/worker` | Minimal: scheduled check runs only |
| Frontend | `apps/web` | 4 screens fully working |
| Infrastructure | `run_local/` | Docker stack: Postgres 16, Redis, MailHog |

### What is deferred

- Warehouse adapters beyond Postgres (MySQL, BigQuery, Snowflake, ClickHouse, Redshift, Databricks, DuckDB, Trino)
- Causal algorithms (PCMCI+, NOTEARS, PC, Granger, DoWhy) → `dqt[causal]`
- Forecast algorithms (Prophet, BOCPD, Matrix Profile) → `dqt[forecast]`
- Deep learning algorithms (autoencoders) → `dqt[deep]`
- SHAP, Bayesian networks, functional dependency → `dqt[explain]`
- HITL active-learning review queue
- Causality layer (causal DAG, Shapley attribution, do-calculus)
- Full lineage (sqlglot parsing, OpenLineage)
- Semantic/metric layer (schema created, no logic)
- On-call schedules, PagerDuty/Slack/Teams notifiers
- AI agent full causal reasoning (agent does basic incident summary only)
- Compatibility shims (GX, Soda, Elementary YAML parsers)
- TimescaleDB + pgvector extensions (plain Postgres 16 for MVP)
- Frontend screens: Lineage, Metrics, Causality, Catalog, On-call, Tasks, Settings

### Build order

1. Repo structure + shared config + Docker stack
2. `packages/dqt` — adapters → algorithms → checks → store → runner
3. DB schema + Alembic migrations
4. `apps/server` — auth → sources → datasets → checks → incidents → agent
5. `apps/web` — AppShell → Overview → Sources wizard → Datasets → Incidents
6. `apps/worker` — arq basics + scheduled runs
7. `packages/dqt-cli` — `demo seed`, `run`, `health-check`
8. Demo seed data + end-to-end validation

---

## 2. Two Database Concepts (Critical Separation)

**dqt metadata DB** — dqt's own control-plane database. Stores: tenants, users, sources config (with encrypted credentials), datasets, columns, checks, check runs, incidents, audit log. dqt owns this database entirely. MVP uses plain **PostgreSQL 16** (no extensions). Designed so that migrating to TimescaleDB later is a one-line `SELECT create_hypertable(...)` call on `check_runs`.

**Monitored warehouses** — the user's actual data warehouses that dqt connects to and reads from. Each is a `Source` record in the metadata DB with encrypted connection credentials. Adapters open **read-only** connections at runtime. dqt never writes to monitored warehouses. A single dqt deployment can monitor many warehouses simultaneously — Postgres, BigQuery, Snowflake, etc. — all completely separate from the metadata DB.

---

## 3. Library (`packages/dqt`)

### Module structure

```
packages/dqt/src/dqt/
├── adapters/
│   ├── _protocol.py            # WarehouseAdapter protocol, HealthCheckResult
│   └── postgres/
│       ├── config.py           # host, port, db, user, password, ssl, schema
│       ├── adapter.py          # ibis-backed WarehouseAdapter impl
│       └── __init__.py
├── algorithms/
│   ├── _base.py                # Detector protocol, DetectorResult, Verdict enum
│   ├── _scales.py              # STAT_SCALES — single source of truth
│   ├── _registry.py            # slug → class registry
│   ├── basic/                  # rule-based threshold checks
│   │   ├── completeness.py     # not_null, null_count, null_percent, not_empty_string
│   │   ├── uniqueness.py       # unique, duplicate_count, duplicate_percent, compound_unique
│   │   ├── validity.py         # in_set, not_in_set, between, match_regex, is_date_parseable, is_json_parseable, custom_sql
│   │   ├── numeric.py          # min_value, max_value, mean_between, median_between, stddev_between, sum_between, percentile_between, variance_between
│   │   └── volume.py           # row_count_between, row_count_equals, freshness, event_freshness, change_rate
│   ├── schema/
│   │   └── schema_checks.py    # column_exists, column_type, schema_match, no_new_columns, no_removed_columns
│   ├── referential/
│   │   └── referential.py      # referential_integrity, cross_dataset_reference
│   ├── distribution/
│   │   ├── shapiro_wilk.py
│   │   ├── anderson_darling.py
│   │   ├── lilliefors.py
│   │   ├── ks1sample.py
│   │   ├── hartigan_dip.py
│   │   ├── skewness.py
│   │   ├── kurtosis.py
│   │   ├── adf.py
│   │   ├── kpss.py
│   │   └── ljung_box.py
│   ├── drift/
│   │   ├── ks2sample.py
│   │   ├── psi.py
│   │   ├── wasserstein1.py
│   │   ├── kl_divergence.py
│   │   ├── jensen_shannon.py
│   │   ├── mmd.py
│   │   ├── chi_square.py
│   │   ├── adwin.py
│   │   └── ddm.py
│   ├── outliers_uni/
│   │   ├── zscore.py
│   │   ├── mad.py              # modified Z-score
│   │   ├── double_mad.py
│   │   ├── iqr.py
│   │   ├── adjusted_boxplot.py # medcouple
│   │   ├── grubbs.py
│   │   ├── gesd.py             # generalised ESD / Rosner
│   │   └── quantile.py
│   ├── outliers_multi/
│   │   ├── mahalanobis.py
│   │   ├── isolation_forest.py
│   │   ├── lof.py
│   │   ├── dbscan.py
│   │   ├── ocsvm.py
│   │   ├── hbos.py
│   │   ├── copod.py
│   │   ├── ecod.py
│   │   └── pca_reconstruction.py
│   ├── timeseries/
│   │   ├── stl.py
│   │   ├── holt_winters.py
│   │   ├── seasonal_esd.py
│   │   ├── cusum.py
│   │   └── page_hinkley.py
│   ├── info/
│   │   ├── cramers_v.py
│   │   ├── theils_u.py
│   │   └── mutual_information.py
│   ├── pattern/
│   │   └── benford.py
│   ├── dimred/
│   │   ├── pca.py
│   │   └── robust_pca.py
│   ├── ensemble/
│   │   ├── normalizer.py
│   │   └── combiner.py         # average, max
│   └── calibration/
│       ├── empirical_cdf.py
│       └── bootstrap_ci.py
├── checks/
│   ├── models.py               # Check, Baseline, RollingWindow (Pydantic v2)
│   ├── loader.py               # YAML → Check
│   └── schema/check.schema.json
├── runner/
│   └── runner.py               # Runner.run(check, source) → RunResult
├── store/
│   ├── _protocol.py            # ResultsStore protocol
│   ├── memory.py               # MemoryStore (default for notebooks/CI)
│   └── postgres.py             # PostgresStore
├── governance/
│   └── models.py               # CatalogEntry — owner, pii, classification, tags, description
├── agent/
│   ├── _protocol.py            # LLMProvider protocol
│   └── anthropic.py            # Claude impl — basic incident summary in MVP
├── lineage/
│   └── models.py               # LineageEdge models only (no sqlglot parsing in MVP)
└── utils/
    └── logging.py              # get_logger() via structlog
```

### Core contracts

**Detector protocol** (`_base.py`):
```python
class Detector(Protocol):
    slug: ClassVar[str]
    def fit(self, reference: pd.DataFrame) -> DetectorState: ...
    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult: ...
```

**DetectorResult**:
```python
@dataclass
class DetectorResult:
    score: float
    verdict: Verdict          # pass | warn | fail
    plain_english: str
    details: dict[str, Any]
```

**Rule-based checks** follow the same protocol with `fit()` as a no-op — no baseline needed, `score()` evaluates the constraint directly against warehouse aggregate results.

**WarehouseAdapter protocol** (`adapters/_protocol.py`):
- `health_check() → HealthCheckResult` — 6 steps: TCP reach → auth → info_schema read → sample SELECT → latency probe → clock skew
- `sample(schema, table, n) → pd.DataFrame`
- `aggregate(schema, table, exprs) → dict`
- `describe_columns(schema, table) → list[ColumnMeta]`
- `list_schemas() → list[str]`
- `list_tables(schema) → list[str]`

**ResultsStore protocol** (`store/_protocol.py`):
- `save_run(run: RunResult) → None`
- `list_runs(check_id, limit) → list[RunResult]`
- `save_incident(incident: Incident) → None`
- `list_incidents(filters) → list[Incident]`

### Algorithm groups in UI taxonomy

| UI tab | Detector groups |
|---|---|
| Basic | `basic`, `schema`, `referential` |
| Distribution | `distribution` |
| Outliers | `outliers_uni`, `outliers_multi` |
| Time series | `timeseries` |
| Drift | `drift` |
| Dependencies | `info`, `ensemble` |
| Auto-baselined | any detector with a baseline config |

### Core library dependencies (non-optional)

```toml
[project.dependencies]
numpy = ">=1.26"
scipy = ">=1.13"
pandas = ">=2.2"
statsmodels = ">=0.14"
scikit-learn = ">=1.5"
pyod = ">=1.1"           # ECOD, COPOD, HBOS, ABOD
diptest = ">=0.6"        # Hartigan's dip
river = ">=0.21"         # ADWIN, DDM/EDDM
structlog = ">=24.0"
pydantic = ">=2.7"
ibis-framework = ">=9.0"
```

### pyproject.toml extras

```toml
[project.optional-dependencies]
postgres = ["psycopg2-binary", "ibis-framework[postgres]"]
causal   = ["tigramite", "dowhy", "causallearn"]        # deferred
forecast = ["prophet", "stumpy"]                         # deferred
deep     = ["torch", "pyod[deep]"]                       # deferred
explain  = ["shap", "pgmpy"]                             # deferred
```

### Hard rule

The library never imports anything from `apps/`. Enforced by a ruff `banned-module-level-imports` rule. The library degrades to `MemoryStore` if no Postgres is configured.

---

## 4. Server (`apps/server`)

### Module structure

```
apps/server/src/dqt_server/
├── main.py                     # FastAPI app, middleware, exception handlers
├── middleware/auth.py          # JWT decode → request.state.*
├── auth/
│   ├── users.py                # fastapi-users, User model
│   ├── permissions.py          # role → allowed actions
│   └── routes.py               # /auth/register, /auth/login, /auth/me
├── tenants/
│   ├── models.py
│   ├── repository.py
│   └── routes.py
├── repositories/base.py        # BaseRepository — tenant scoping, soft delete, pagination
├── sources/
│   ├── models.py               # Source (encrypted creds)
│   ├── repository.py
│   ├── services.py             # health_check(), test_connection()
│   └── routes.py
├── datasets/
│   ├── models.py               # Dataset, Column (with catalog metadata)
│   ├── repository.py
│   ├── services.py             # sync_columns(), sample(), describe()
│   └── routes.py
├── checks/
│   ├── models.py               # Check, CheckRun
│   ├── repository.py
│   ├── services.py             # run_check(), schedule_check()
│   └── routes.py
├── incidents/
│   ├── models.py               # Incident, IncidentComment
│   ├── repository.py
│   ├── services.py             # lifecycle transitions, auto-resolve
│   └── routes.py
├── agent/
│   ├── services.py             # invoke Claude → structured explanation
│   └── routes.py               # POST /explain
├── db/
│   ├── engine.py               # async SQLAlchemy engine + session factory
│   ├── schema_core.sql
│   ├── schema_checks.sql
│   ├── schema_incidents.sql
│   └── migrations/             # Alembic
├── scripts/dump_openapi.py
└── worker_tasks.py             # arq task stubs
```

### API surface (`/api/v1`)

| Method | Path | Description |
|---|---|---|
| POST | `/auth/login` | JWT token |
| POST | `/auth/register` | New user + tenant |
| GET | `/auth/me` | Current user |
| GET | `/sources` | List sources |
| POST | `/sources` | Create source |
| GET | `/sources/{id}` | Source detail |
| PUT | `/sources/{id}` | Update source |
| DELETE | `/sources/{id}` | Delete source |
| POST | `/sources/{id}/health-check` | 6-step health check |
| GET | `/sources/{id}/wizard/tables` | Tables available to watch |
| GET | `/datasets` | List datasets with latest health |
| POST | `/datasets` | Register dataset from source |
| GET | `/datasets/{id}` | Dataset detail + columns |
| GET | `/datasets/{id}/sample` | Row sample |
| POST | `/datasets/{id}/sync` | Re-sync column metadata |
| GET | `/checks` | List checks |
| POST | `/checks` | Create check |
| GET | `/checks/{id}` | Check detail |
| PUT | `/checks/{id}` | Update check |
| DELETE | `/checks/{id}` | Delete check |
| POST | `/checks/{id}/run` | On-demand run |
| GET | `/checks/{id}/runs` | Run history |
| GET | `/incidents` | List incidents (filterable) |
| GET | `/incidents/{id}` | Incident detail + evidence |
| PATCH | `/incidents/{id}` | Lifecycle transition |
| POST | `/incidents/{id}/comments` | Add comment |
| POST | `/agent/explain` | Explain incident (sync) — MVP scope below |
| WS | `/ws` | Live incident + run feed |

### Key decisions

- Credentials encrypted at rest with `cryptography.fernet`; key from env var `DQT_CREDS_KEY`
- `TenantScopedRepository` injects `tenant_id` on every query
- All routes async; SQLAlchemy 2.x async sessions throughout
- Error envelope: `{"error": {"code": "...", "message": "...", "trace_id": "..."}}`
- WebSocket broadcasts `incident.opened`, `incident.resolved`, `check_run.completed` events
- Roles: `viewer` / `editor` / `admin` / `sysadmin`

**MVP agent scope** (`POST /agent/explain`): calls Claude with the incident's structured context — detector slug, score, plain_english verdict, dataset name, column name, check params, and the last 5 check run scores for trend context. Returns `{plain_english: str, evidence: list[{kind, description, value}], confidence: float, follow_up_questions: list[str]}`. No DAG traversal, no do-calculus, no lineage walking in MVP.

**Generated types**: `packages/dqt-types/` is the generated TypeScript package produced by running `make types` (openapi-typescript from the server's `/openapi.json`). Output goes to `apps/web/src/generated/api.ts` and is git-ignored. Frontend never imports manually written API types — only the generated ones.

---

## 5. Frontend (`apps/web`)

### Structure

```
apps/web/src/
├── app/
│   ├── (auth)/login/page.tsx
│   └── (app)/
│       ├── layout.tsx                  # AppShell
│       ├── overview/page.tsx
│       ├── sources/
│       │   ├── page.tsx
│       │   └── new/postgres/page.tsx   # 3-step wizard
│       ├── datasets/
│       │   ├── page.tsx
│       │   └── [id]/page.tsx
│       └── incidents/
│           ├── page.tsx
│           └── [id]/page.tsx
├── components/
│   ├── ui/                             # shadcn primitives
│   ├── charts/
│   │   ├── StatGauge.tsx
│   │   ├── StatChip.tsx
│   │   ├── Spark.tsx
│   │   ├── TimeSeries.tsx
│   │   ├── HistDual.tsx
│   │   └── CDFPair.tsx
│   └── shared/
│       ├── AppShell.tsx
│       ├── InfoTip.tsx
│       ├── StatusDot.tsx
│       └── EngineGlyph.tsx
├── modules/
│   ├── overview/components/ hooks/ services/
│   ├── sources/components/ hooks/ services/
│   ├── datasets/components/ hooks/ services/
│   └── incidents/components/ hooks/ services/
├── lib/
│   ├── api.ts                          # typed OpenAPI client (React Query)
│   ├── stats.ts                        # reads STAT_SCALES for StatGauge
│   └── error-handling.ts
├── messages/en/
│   ├── common.json
│   ├── overview.json
│   ├── sources.json
│   ├── datasets.json
│   └── incidents.json
└── generated/api.ts                    # git-ignored, from openapi-typescript
```

### Screen specs

**Overview** — fleet KPI band (open incidents / datasets watched / checks passing / mean detect time), algorithm-group coverage cards, datasets table with sparklines and health badges, activity feed.

**Sources + wizard** — engine card grid (Postgres active, others greyed out). Wizard step 1: Configure (host/port/db/user/password/ssl). Step 2: Test & Verify (live 6-step health check, each step shows pass/fail with latency). Step 3: Choose Tables (checkbox list). Forward disabled until current step is valid.

**Datasets** — list with latest check verdict, sparkline, row count, last run time. Detail: left column list, right panel with `HistDual` + `CDFPair` + `StatGauge` bank for every check on the selected column.

**Incidents** — filterable list (severity / status / dataset / date range). KPI band. Detail: statistical evidence section, segment decomposition, agent explanation panel (plain English + cited evidence with links), activity log + comments, related incidents rail.

### Design system

- Zero border-radius everywhere, 1px borders, sharp corners
- JetBrains Mono (weight 300) for stat values, KPIs, code; Inter Tight for UI
- Accent `#9DD0B0`, pass `#7FB394`, warn `#D9B566`, fail `#E07B6E`
- Dark default (`data-theme="dark"`), light supported, toggle persisted in `localStorage`
- 220ms fadeIn on screen mount, 240ms ease-out on bar widths, no other motion
- `StatGauge` reads `STAT_SCALES` from `lib/stats.ts` — never hardcode thresholds in components

---

## 6. Infrastructure

### Docker stack (`run_local/docker-compose.yml`)

| Service | Image | Port | Purpose |
|---|---|---|---|
| postgres | `postgres:16` | 5434 | dqt metadata DB |
| redis | `redis:7-alpine` | 6379 | arq broker + rate limiting |
| mailhog | `mailhog/mailhog` | 8025 | email catch-all |
| adminer | `adminer` | 8081 | DB browser |

### dqt metadata DB schema (key tables)

```sql
tenants           (id, name, created_at)
users             (id, tenant_id, email, hashed_password, role, created_at)
user_sessions     (id, user_id, token_hash, expires_at)
sources           (id, tenant_id, engine, display_name, host, port, dbname,
                   username, encrypted_password, ssl_mode, extra_config, created_at)
datasets          (id, source_id, tenant_id, schema_name, table_name,
                   row_count, last_synced_at, created_at)
columns           (id, dataset_id, name, data_type, pii, owner,
                   classification, description, tags, created_at)
checks            (id, tenant_id, dataset_id, column_id, detector_slug,
                   params, baseline_config, schedule, created_at)
check_runs        (id, check_id, started_at, finished_at, verdict,
                   score, plain_english, details)
incidents         (id, tenant_id, check_id, check_run_id, opened_at,
                   resolved_at, status, severity, score, detector_slug)
incident_comments (id, incident_id, user_id, body, created_at)
audit_log         (id, tenant_id, actor_id, action, target_type,
                   target_id, payload, created_at)
```

`check_runs` uses a regular index on `started_at` in MVP. Migrating to a TimescaleDB hypertable later is a single DDL call.

### Migrations

Alembic manages all schema changes. `make db-migrate` runs `alembic upgrade head`. Initial migration creates all tables above.

### Demo seed data

`dqt demo seed` populates:
- 1 tenant + 1 admin user
- 1 Postgres source (pointing at a synthetic `analytics` schema in the same DB)
- 3 datasets: `fct_orders`, `fct_sessions`, `dim_customers`
- ~20 checks across the datasets (mix of rule-based and statistical)
- Pre-run check history with injected anomalies
- 3 open incidents so Overview and Incidents screens aren't empty on first load

### Worker (`apps/worker`)

Minimal arq setup. One task: `run_scheduled_checks` — polls `checks` table for due checks, runs them via the library, fires incidents on fail/warn. Agent invocation is synchronous from the server in MVP; no agent loop in the worker.

---

## 7. Testing Strategy

**Library tests** (`packages/dqt/tests/`):
- Unit only, `MemoryStore`, no Postgres required
- Every detector: known-answer test, synthetic drift/no-drift test, hypothesis property test, golden-file STAT_SCALE verdict
- Must complete in <60s
- Run with: `make test-lib`

**Server tests** (`apps/server/tests/`):
- Unit tests: mock the library, test route logic and error handling
- Integration tests: real Postgres via testcontainers (port 5436), real library
- Run with: `make test-server-unit` / `make test-server-int`

**Frontend tests** (`apps/web/`):
- Vitest for component unit tests
- No Playwright in MVP
- Run with: `cd apps/web && pnpm test`

---

## 8. How to Run

```bash
# First time
make install                  # uv sync + pnpm install
./run_local/start.sh          # Docker stack up + migrations + demo seed

# Daily dev
make dev-server               # FastAPI on :8000 (hot reload)
make dev-web                  # Next.js on :3000 (hot reload)

# Validate
make test-lib                 # library tests (<60s)
make lint                     # ruff + mypy + eslint + tsc
open http://localhost:3000
```

---

## 9. GitHub

Remote: `https://github.com/antonbarr-data/dqt`  
All work committed and pushed to this repo throughout the build.
