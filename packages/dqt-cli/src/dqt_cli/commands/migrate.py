"""dqt migrate -- apply schema migrations for Phase 2 tables.

Tables created:
  dqt_metric_pins         -- user-pinned metrics
  dqt_check_suggestions   -- accepted/rejected check suggestions
  dqt_causal_reviews_v2   -- causal edge review decisions
  dqt_ui_feedback         -- thumbs-up/down on narratives

Idempotent (CREATE TABLE IF NOT EXISTS). --dry-run prints SQL without executing.
"""
from __future__ import annotations

import typer

_MIGRATIONS: list[tuple[str, str]] = [
    (
        "dqt_metric_pins",
        """CREATE TABLE IF NOT EXISTS dqt_metric_pins (
    id          SERIAL PRIMARY KEY,
    user_id     TEXT NOT NULL,
    metric_fqn  TEXT NOT NULL,
    pinned_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, metric_fqn)
);""",
    ),
    (
        "dqt_check_suggestions",
        """CREATE TABLE IF NOT EXISTS dqt_check_suggestions (
    id              SERIAL PRIMARY KEY,
    dataset_id      TEXT NOT NULL,
    column_name     TEXT NOT NULL,
    detector_slug   TEXT NOT NULL,
    params          JSONB DEFAULT '{}',
    rationale       TEXT,
    confidence      FLOAT,
    decision        TEXT CHECK (decision IN ('accepted', 'rejected', 'pending')) DEFAULT 'pending',
    decided_by      TEXT,
    decided_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);""",
    ),
    (
        "dqt_causal_reviews_v2",
        """CREATE TABLE IF NOT EXISTS dqt_causal_reviews_v2 (
    id                  TEXT PRIMARY KEY,
    cause_metric_fqn    TEXT NOT NULL,
    effect_metric_fqn   TEXT NOT NULL,
    p_value             FLOAT,
    evidence_strength   TEXT,
    weight_delta        FLOAT DEFAULT 0.0,
    status              TEXT CHECK (status IN ('pending', 'accepted', 'rejected')) DEFAULT 'pending',
    reviewer            TEXT,
    notes               TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    reviewed_at         TIMESTAMPTZ
);""",
    ),
    (
        "dqt_ui_feedback",
        """CREATE TABLE IF NOT EXISTS dqt_ui_feedback (
    id              SERIAL PRIMARY KEY,
    user_id         TEXT,
    metric_fqn      TEXT NOT NULL,
    window_start    TIMESTAMPTZ,
    window_end      TIMESTAMPTZ,
    rating          SMALLINT CHECK (rating IN (-1, 1)),
    comment         TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);""",
    ),
]


def migrate_command(
    database_url: str = typer.Option(
        None,
        "--database-url",
        envvar="DATABASE_URL",
        help="PostgreSQL connection string. Defaults to DATABASE_URL env var.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print SQL without executing."),
) -> None:
    """Apply Phase 2 schema migrations (idempotent)."""
    if dry_run:
        typer.echo("-- DRY RUN: the following statements would be executed\n")
        for table, sql in _MIGRATIONS:
            typer.echo(f"-- {table}")
            typer.echo(sql)
            typer.echo()
        return

    if not database_url:
        typer.echo(
            "Error: DATABASE_URL is required. Pass --database-url or set DATABASE_URL.",
            err=True,
        )
        raise typer.Exit(code=1)

    try:
        import psycopg2
    except ImportError:
        typer.echo("Error: psycopg2 is required. Run: pip install psycopg2-binary", err=True)
        raise typer.Exit(code=1)

    conn = psycopg2.connect(database_url)
    conn.autocommit = True
    cur = conn.cursor()
    applied = 0
    for table, sql in _MIGRATIONS:
        try:
            cur.execute(sql)
            typer.echo(f"  ok  {table}")
            applied += 1
        except Exception as exc:
            typer.echo(f"  err {table}: {exc}", err=True)
    cur.close()
    conn.close()
    typer.echo(f"\n{applied}/{len(_MIGRATIONS)} migrations applied.")
