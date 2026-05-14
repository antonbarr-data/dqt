-- dqt production schema
-- Creates all tables for the dqt server in an empty PostgreSQL 16+ database.
-- Requires: TimescaleDB extension, pgvector extension.
-- Run once against a fresh database:
--   psql $DATABASE_URL -f apps/server/db/schema.sql

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------

CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "vector";      -- pgvector semantic embeddings
CREATE EXTENSION IF NOT EXISTS "timescaledb"; -- time-series hypertables

-- ---------------------------------------------------------------------------
-- Tenants
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS tenants (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    slug       TEXT        UNIQUE NOT NULL,
    name       TEXT        NOT NULL,
    plan       TEXT        NOT NULL DEFAULT 'free',  -- free / pro / enterprise
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Users
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS users (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT        UNIQUE NOT NULL,
    hashed_password TEXT,
    google_id       TEXT        UNIQUE,
    role            TEXT        NOT NULL DEFAULT 'viewer',  -- viewer/editor/admin/oncall/sysadmin
    tenant_id       TEXT        NOT NULL DEFAULT 'default',
    is_active       BOOLEAN     NOT NULL DEFAULT true,
    preferred_language TEXT     NOT NULL DEFAULT 'en',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);

-- ---------------------------------------------------------------------------
-- Sources (warehouse connections)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS sources (
    id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id             TEXT        NOT NULL,
    name                  TEXT        NOT NULL,
    engine                TEXT        NOT NULL,  -- postgres/mysql/bigquery/snowflake/clickhouse/redshift/databricks/duckdb/trino
    connection_params     JSONB       NOT NULL DEFAULT '{}',
    credentials_ref       TEXT,                  -- Secret Manager key name
    status                TEXT        NOT NULL DEFAULT 'pending',  -- pending/healthy/degraded/unreachable
    last_health_check_at  TIMESTAMPTZ,
    health_details        JSONB       NOT NULL DEFAULT '{}',
    max_bytes_per_query   BIGINT,
    owner                 TEXT,
    tags                  TEXT[]      NOT NULL DEFAULT '{}',
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at            TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_sources_tenant ON sources(tenant_id) WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- Datasets & Columns
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS datasets (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           TEXT        NOT NULL,
    source_id           UUID        NOT NULL REFERENCES sources(id),
    schema_name         TEXT        NOT NULL,
    table_name          TEXT        NOT NULL,
    row_count           BIGINT,
    size_bytes          BIGINT,
    last_profiled_at    TIMESTAMPTZ,
    freshness_sla_seconds INT,
    owner               TEXT,
    domain              TEXT,
    description         TEXT,
    classification      TEXT        NOT NULL DEFAULT 'internal',  -- public/internal/confidential/restricted
    pii                 BOOLEAN     NOT NULL DEFAULT false,
    tags                TEXT[]      NOT NULL DEFAULT '{}',
    dbt_unique_id       TEXT,
    meta                JSONB       NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ,
    UNIQUE (source_id, schema_name, table_name)
);
CREATE INDEX IF NOT EXISTS idx_datasets_tenant ON datasets(tenant_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_datasets_source ON datasets(source_id) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS columns (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id       UUID        NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    tenant_id        TEXT        NOT NULL,
    column_name      TEXT        NOT NULL,
    data_type        TEXT        NOT NULL,
    nullable         BOOLEAN     NOT NULL DEFAULT true,
    ordinal_position INT         NOT NULL,
    description      TEXT,
    pii              BOOLEAN     NOT NULL DEFAULT false,
    classification   TEXT        NOT NULL DEFAULT 'internal',
    tags             TEXT[]      NOT NULL DEFAULT '{}',
    embedding        VECTOR(1536),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (dataset_id, column_name)
);
CREATE INDEX IF NOT EXISTS idx_columns_dataset ON columns(dataset_id);
CREATE INDEX IF NOT EXISTS idx_columns_tenant  ON columns(tenant_id);

-- Approximate nearest-neighbour index for semantic column search.
-- Requires at least one row before building; create after initial data load.
-- CREATE INDEX ON columns USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE IF NOT EXISTS column_profiles (
    id              UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    column_id       UUID             NOT NULL REFERENCES columns(id) ON DELETE CASCADE,
    profiled_at     TIMESTAMPTZ      NOT NULL,
    row_count       BIGINT           NOT NULL,
    null_count      BIGINT           NOT NULL,
    distinct_count  BIGINT,
    min_val         TEXT,
    max_val         TEXT,
    mean_val        DOUBLE PRECISION,
    stddev_val      DOUBLE PRECISION,
    p25             DOUBLE PRECISION,
    p50             DOUBLE PRECISION,
    p75             DOUBLE PRECISION,
    histogram_bins  JSONB,           -- [{edge, count}]
    top_values      JSONB,           -- [{value, count, fraction}]
    data_type_group TEXT             -- numeric/string/date/boolean
);
CREATE INDEX IF NOT EXISTS idx_column_profiles_col ON column_profiles(column_id, profiled_at DESC);

-- ---------------------------------------------------------------------------
-- Checks & Runs
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS checks (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           TEXT        NOT NULL,
    dataset_id          UUID        NOT NULL REFERENCES datasets(id),
    column_id           UUID        REFERENCES columns(id),   -- NULL = table-level
    detector_slug       TEXT        NOT NULL,
    detector_params     JSONB       NOT NULL DEFAULT '{}',
    name                TEXT,
    group_name          TEXT,        -- auto-baselined/distribution/timeseries/outliers/dependencies/schema/basic
    schedule            TEXT,        -- cron expression; NULL = on-demand only
    enabled             BOOLEAN     NOT NULL DEFAULT true,
    baseline_window_days INT        NOT NULL DEFAULT 14,
    warn_threshold      DOUBLE PRECISION,   -- NULL = use STAT_SCALES defaults
    fail_threshold      DOUBLE PRECISION,
    owner               TEXT,
    tags                TEXT[]      NOT NULL DEFAULT '{}',
    yaml_definition     TEXT,        -- raw YAML (SodaCL-compatible)
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_checks_dataset ON checks(dataset_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_checks_tenant  ON checks(tenant_id)  WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS baselines (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    check_id         UUID        NOT NULL REFERENCES checks(id) ON DELETE CASCADE,
    detector_slug    TEXT        NOT NULL,
    detector_version TEXT        NOT NULL DEFAULT '1',
    state_json       JSONB       NOT NULL,   -- serialised fit() output
    fit_from         TIMESTAMPTZ NOT NULL,
    fit_until        TIMESTAMPTZ NOT NULL,
    row_count        INT         NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_baselines_check ON baselines(check_id, created_at DESC);

CREATE TABLE IF NOT EXISTS check_runs (
    id               UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        TEXT             NOT NULL,
    check_id         UUID             NOT NULL REFERENCES checks(id),
    baseline_id      UUID             REFERENCES baselines(id),
    detector_slug    TEXT             NOT NULL,
    detector_version TEXT             NOT NULL DEFAULT '1',
    started_at       TIMESTAMPTZ      NOT NULL,
    finished_at      TIMESTAMPTZ      NOT NULL,
    verdict          TEXT             NOT NULL,  -- pass/warn/fail
    score            DOUBLE PRECISION NOT NULL,
    plain_english    TEXT             NOT NULL,
    details          JSONB            NOT NULL DEFAULT '{}',
    diagnostic_sql   TEXT,
    triggered_by     TEXT             NOT NULL DEFAULT 'schedule',  -- schedule/manual/api
    proof_commitment TEXT
);
CREATE INDEX IF NOT EXISTS idx_check_runs_check  ON check_runs(check_id, finished_at DESC);
CREATE INDEX IF NOT EXISTS idx_check_runs_tenant ON check_runs(tenant_id, finished_at DESC);

-- ---------------------------------------------------------------------------
-- Incidents (full lifecycle)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS incidents (
    id                     UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id              TEXT             NOT NULL,
    check_id               UUID             NOT NULL REFERENCES checks(id),
    run_id                 UUID             NOT NULL REFERENCES check_runs(id),
    detector_slug          TEXT             NOT NULL,
    severity               TEXT             NOT NULL,  -- warn/fail
    status                 TEXT             NOT NULL DEFAULT 'open',
    -- ^ open/investigating/resolved/closed/snoozed/auto_resolved
    title                  TEXT,
    opened_at              TIMESTAMPTZ      NOT NULL DEFAULT now(),
    acknowledged_at        TIMESTAMPTZ,
    resolved_at            TIMESTAMPTZ,
    closed_at              TIMESTAMPTZ,
    snoozed_until          TIMESTAMPTZ,
    score                  DOUBLE PRECISION NOT NULL,
    assignee_id            UUID             REFERENCES users(id),
    auto_resolve_after_runs INT             NOT NULL DEFAULT 3,
    consecutive_pass_count  INT             NOT NULL DEFAULT 0,
    agent_explanation_id   UUID,            -- FK added after agent_explanations is created
    meta                   JSONB            NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_incidents_tenant_status ON incidents(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_incidents_check         ON incidents(check_id, opened_at DESC);

CREATE TABLE IF NOT EXISTS incident_comments (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID        NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    author_id   UUID        NOT NULL REFERENCES users(id),
    body        TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_incident_comments_incident ON incident_comments(incident_id);

CREATE TABLE IF NOT EXISTS incident_tasks (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID        NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    tenant_id   TEXT        NOT NULL,
    kind        TEXT        NOT NULL,  -- acknowledge/investigate/mitigate/postmortem
    title       TEXT        NOT NULL,
    assignee_id UUID        REFERENCES users(id),
    status      TEXT        NOT NULL DEFAULT 'open',  -- open/in_progress/done
    due_at      TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_incident_tasks_tenant ON incident_tasks(tenant_id, status);

CREATE TABLE IF NOT EXISTS postmortems (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID        NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    body_md     TEXT        NOT NULL DEFAULT '',
    generated_by TEXT       NOT NULL DEFAULT 'agent',  -- agent/manual
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Metrics (semantic layer)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS metrics (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       TEXT        NOT NULL,
    slug            TEXT        NOT NULL,
    name            TEXT        NOT NULL,
    kind            TEXT        NOT NULL,  -- sum/count/ratio/model
    source_expr     TEXT        NOT NULL,
    description     TEXT,
    unit            TEXT,
    owner           TEXT,
    domain          TEXT,
    tags            TEXT[]      NOT NULL DEFAULT '{}',
    embedding       VECTOR(1536),
    yaml_definition TEXT,
    dbt_metric_name TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ,
    UNIQUE (tenant_id, slug)
);
CREATE INDEX IF NOT EXISTS idx_metrics_tenant ON metrics(tenant_id) WHERE deleted_at IS NULL;

-- CREATE INDEX ON metrics USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE IF NOT EXISTS metric_dimensions (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_id UUID NOT NULL REFERENCES metrics(id) ON DELETE CASCADE,
    name      TEXT NOT NULL,
    expr      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS metric_runs (
    id                UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_id         UUID             NOT NULL REFERENCES metrics(id),
    tenant_id         TEXT             NOT NULL,
    measured_at       TIMESTAMPTZ      NOT NULL,
    value             DOUBLE PRECISION NOT NULL,
    dimension_filters JSONB            NOT NULL DEFAULT '{}',
    source_run_id     UUID             REFERENCES check_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_metric_runs_metric ON metric_runs(metric_id, measured_at DESC);

-- ---------------------------------------------------------------------------
-- Causality
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS causal_edges (
    id               UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        TEXT             NOT NULL,
    cause_metric_id  UUID             NOT NULL REFERENCES metrics(id),
    effect_metric_id UUID             NOT NULL REFERENCES metrics(id),
    method           TEXT             NOT NULL DEFAULT 'pcmci',  -- pcmci/granger/te
    lag_periods      INT              NOT NULL DEFAULT 1,
    weight           DOUBLE PRECISION NOT NULL,
    e_value          DOUBLE PRECISION,   -- sensitivity to unobserved confounders
    stability_score  DOUBLE PRECISION,
    status           TEXT             NOT NULL DEFAULT 'proposed',  -- proposed/confirmed/rejected
    discovered_at    TIMESTAMPTZ      NOT NULL DEFAULT now(),
    confirmed_at     TIMESTAMPTZ,
    report_id        UUID,
    UNIQUE (tenant_id, cause_metric_id, effect_metric_id, method)
);
CREATE INDEX IF NOT EXISTS idx_causal_edges_tenant ON causal_edges(tenant_id, status);

CREATE TABLE IF NOT EXISTS causal_reports (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        TEXT        NOT NULL,
    ran_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    n_metrics        INT         NOT NULL,
    n_edges_proposed INT         NOT NULL,
    params           JSONB       NOT NULL DEFAULT '{}'
);

-- ---------------------------------------------------------------------------
-- Lineage
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS lineage_edges (
    id                 UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          TEXT             NOT NULL,
    upstream_dataset   TEXT             NOT NULL,
    upstream_column    TEXT,
    downstream_dataset TEXT             NOT NULL,
    downstream_column  TEXT,
    transform_kind     TEXT,            -- select/join/agg/passthrough
    confidence         DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    source_kind        TEXT             NOT NULL DEFAULT 'sql',  -- sql/dbt/openlineage
    discovered_at      TIMESTAMPTZ      NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_lineage_downstream ON lineage_edges(tenant_id, downstream_dataset);
CREATE INDEX IF NOT EXISTS idx_lineage_upstream   ON lineage_edges(tenant_id, upstream_dataset);

-- ---------------------------------------------------------------------------
-- Governance
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS policies (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   TEXT        NOT NULL,
    name        TEXT        NOT NULL,
    yaml_body   TEXT        NOT NULL,
    enabled     BOOLEAN     NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL   PRIMARY KEY,
    tenant_id   TEXT        NOT NULL,
    actor_id    UUID        REFERENCES users(id),
    act_as_id   UUID        REFERENCES users(id),   -- sysadmin emulation target
    action      TEXT        NOT NULL,
    target_type TEXT        NOT NULL,
    target_id   TEXT        NOT NULL,
    before_json JSONB,
    after_json  JSONB,
    ip          TEXT,
    user_agent  TEXT,
    trace_id    TEXT,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_log_tenant ON audit_log(tenant_id, occurred_at DESC);

-- ---------------------------------------------------------------------------
-- On-call
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS oncall_schedules (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     TEXT        NOT NULL,
    name          TEXT        NOT NULL,
    timezone      TEXT        NOT NULL DEFAULT 'UTC',
    rotation_days INT         NOT NULL DEFAULT 7,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS oncall_schedule_members (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id UUID        NOT NULL REFERENCES oncall_schedules(id) ON DELETE CASCADE,
    user_id     UUID        NOT NULL REFERENCES users(id),
    position    INT         NOT NULL,   -- rotation order
    starts_at   TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS escalation_policies (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   TEXT        NOT NULL,
    name        TEXT        NOT NULL,
    steps       JSONB       NOT NULL DEFAULT '[]',  -- [{delay_min, schedule_id, channel_ids}]
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notification_channels (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   TEXT        NOT NULL,
    kind        TEXT        NOT NULL,   -- slack/teams/email/pagerduty/opsgenie/webhook
    name        TEXT        NOT NULL,
    config      JSONB       NOT NULL DEFAULT '{}',
    enabled     BOOLEAN     NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- HITL queue
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS hitl_queue (
    id          UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   TEXT             NOT NULL,
    kind        TEXT             NOT NULL,   -- causal_edge/incident_class/semantic_mapping/check_suggestion
    target_id   UUID             NOT NULL,
    uncertainty DOUBLE PRECISION NOT NULL,
    status      TEXT             NOT NULL DEFAULT 'pending',  -- pending/reviewed/skipped
    label       JSONB,
    reviewer_id UUID             REFERENCES users(id),
    reviewed_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ      NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_hitl_queue_tenant ON hitl_queue(tenant_id, status, uncertainty DESC);

-- ---------------------------------------------------------------------------
-- Agent explanations
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS agent_explanations (
    id                  UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           TEXT             NOT NULL,
    incident_id         UUID             REFERENCES incidents(id),
    evidence_hash       TEXT             NOT NULL,
    plain_english       TEXT             NOT NULL,
    evidence_json       JSONB            NOT NULL DEFAULT '[]',
    confidence          DOUBLE PRECISION,
    follow_up_questions JSONB            NOT NULL DEFAULT '[]',
    model_id            TEXT             NOT NULL,
    created_at          TIMESTAMPTZ      NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, evidence_hash)
);

-- Now that agent_explanations exists, add the deferred FK on incidents.
ALTER TABLE incidents
    ADD CONSTRAINT fk_incidents_agent_explanation
    FOREIGN KEY (agent_explanation_id) REFERENCES agent_explanations(id);

-- ---------------------------------------------------------------------------
-- Library-level store tables (used by the standalone dqt library)
-- These are created by PostgresStore._ensure_schema() but included here
-- so a fresh DB has everything in one shot.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS dqt_runs (
    run_id           UUID             PRIMARY KEY,
    check_id         UUID             NOT NULL,
    detector_slug    TEXT             NOT NULL,
    detector_version TEXT             NOT NULL DEFAULT '1',
    started_at       TIMESTAMPTZ      NOT NULL,
    finished_at      TIMESTAMPTZ      NOT NULL,
    verdict          TEXT             NOT NULL,
    score            DOUBLE PRECISION NOT NULL,
    plain_english    TEXT             NOT NULL,
    details          JSONB            NOT NULL DEFAULT '{}',
    diagnostic_sql   TEXT
);
CREATE INDEX IF NOT EXISTS idx_dqt_runs_check ON dqt_runs(check_id, finished_at DESC);

CREATE TABLE IF NOT EXISTS dqt_incidents (
    incident_id UUID             PRIMARY KEY,
    check_id    UUID             NOT NULL,
    run_id      UUID             NOT NULL,
    detector_slug TEXT           NOT NULL,
    severity    TEXT             NOT NULL,
    opened_at   TIMESTAMPTZ      NOT NULL,
    score       DOUBLE PRECISION NOT NULL,
    status      TEXT             NOT NULL DEFAULT 'open',
    resolved_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_dqt_incidents_check ON dqt_incidents(check_id);

CREATE TABLE IF NOT EXISTS dqt_proofs (
    commitment           TEXT        PRIMARY KEY,
    run_id               UUID        NOT NULL,
    check_id             UUID        NOT NULL,
    detector_slug        TEXT        NOT NULL,
    detector_version     TEXT        NOT NULL,
    data_hash            TEXT        NOT NULL,
    row_count            INTEGER     NOT NULL,
    commitment_algorithm TEXT        NOT NULL DEFAULT 'sha256',
    computed_at          TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dqt_proofs_check ON dqt_proofs(check_id);

CREATE TABLE IF NOT EXISTS dqt_causal_reviews (
    review_id   UUID        PRIMARY KEY,
    edge_id     UUID        NOT NULL,
    cause       TEXT        NOT NULL,
    effect      TEXT        NOT NULL,
    decision    TEXT        NOT NULL,
    reviewer    TEXT        NOT NULL,
    reviewed_at TIMESTAMPTZ NOT NULL,
    reason      TEXT        NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_dqt_causal_reviews_edge ON dqt_causal_reviews(edge_id);

-- ---------------------------------------------------------------------------
-- TimescaleDB hypertables
-- Convert the five time-series-heavy tables after initial creation.
-- Safe to run multiple times (if_not_exists => true).
-- ---------------------------------------------------------------------------

SELECT create_hypertable('check_runs',      'finished_at', if_not_exists => true);
SELECT create_hypertable('metric_runs',     'measured_at',  if_not_exists => true);
SELECT create_hypertable('column_profiles', 'profiled_at',  if_not_exists => true);
SELECT create_hypertable('incidents',       'opened_at',    if_not_exists => true);
SELECT create_hypertable('audit_log',       'occurred_at',  if_not_exists => true);
