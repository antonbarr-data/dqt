#!/usr/bin/env python3
"""
dqt database deployment script.

Idempotent -- safe to run against an empty, partial, or fully-deployed
Postgres database. Creates all missing tables, applies backward-compat
column additions, and seeds all reference + auth data.

Usage (from repo root):
    uv run python scripts/deploy_db.py
    uv run python scripts/deploy_db.py --url postgresql://user:pass@host/db
    DATABASE_URL=... uv run python scripts/deploy_db.py
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SERVER_SRC = REPO_ROOT / "apps" / "server" / "src"
sys.path.insert(0, str(SERVER_SRC))


def _load_dotenv() -> None:
    """Parse env files from repo root without requiring python-dotenv.

    Load order (later files do NOT override earlier ones):
      1. local.env  -- local dev overrides (DATABASE_URL for localhost)
      2. .env       -- secrets (API keys, production credentials)
    """
    for candidate in [REPO_ROOT / "local.env", REPO_ROOT / ".env"]:
        if not candidate.exists():
            continue
        with open(candidate) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key not in os.environ:
                    os.environ[key] = val
        print(f"  env loaded from {candidate.relative_to(REPO_ROOT)}")


def _normalise_url(url: str) -> str:
    """Ensure URL uses the asyncpg driver."""
    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


async def deploy(override_url: str | None = None) -> None:
    print("=== dqt database deployment ===\n")

    # --- resolve URL before importing dqt_server (engine created at import time) ---
    _load_dotenv()
    raw_url = override_url or os.environ.get("DATABASE_URL", "")
    if not raw_url:
        print("ERROR: DATABASE_URL not set. Pass --url or add it to .env")
        sys.exit(1)
    url = _normalise_url(raw_url)
    host_part = url.split("@")[-1] if "@" in url else url
    print(f"  target: {host_part}\n")

    # --- deferred imports so engine.py sees DATABASE_URL ---
    os.environ.setdefault("DATABASE_URL", url)

    from sqlalchemy import inspect as sa_inspect, text
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from dqt_server.db.engine import Base
    # Import all model modules to register their tables with Base
    import dqt_server.auth.models  # noqa: F401
    import dqt_server.models.core  # noqa: F401
    import dqt_server.models.ref_data  # noqa: F401

    from dqt_server.auth.models import ROLE_SYSADMIN, User
    from dqt_server.auth.service import SEEDED_SYSADMIN_EMAIL
    from dqt_server.ref_data import ISO_COUNTRIES, ISO_CURRENCIES
    from dqt_server.ref_data_languages import ISO_LANGUAGES
    from dqt_server.ref_data_timezones import ISO_TIMEZONES
    from dqt_server.ref_data_regions import ISO_REGIONS
    from sqlalchemy import select

    engine = create_async_engine(url, pool_pre_ping=True, pool_size=3, max_overflow=5)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # ------------------------------------------------------------------ #
    # 1. Create all tables                                                 #
    # ------------------------------------------------------------------ #
    print("[1/3] Schema -- creating missing tables")
    async with engine.begin() as conn:
        existing_before: set[str] = await conn.run_sync(
            lambda c: set(sa_inspect(c).get_table_names())
        )
        await conn.run_sync(Base.metadata.create_all)
        existing_after: set[str] = await conn.run_sync(
            lambda c: set(sa_inspect(c).get_table_names())
        )

    created = sorted(existing_after - existing_before)
    skipped = sorted(existing_after & existing_before)
    if created:
        for t in created:
            print(f"  CREATED  {t}")
    else:
        print(f"  all {len(skipped)} tables already present")
    if skipped and created:
        print(f"  EXISTS   {len(skipped)} tables already present")

    # ------------------------------------------------------------------ #
    # 2. Backward-compat column additions                                  #
    # ------------------------------------------------------------------ #
    print("\n[2/3] Schema -- backward-compat column additions")
    column_migrations: list[tuple[str, str, str]] = [
        ("sources", "password", "ALTER TABLE sources ADD COLUMN IF NOT EXISTS password VARCHAR"),
        ("sources", "secure",   "ALTER TABLE sources ADD COLUMN IF NOT EXISTS secure BOOLEAN NOT NULL DEFAULT FALSE"),
    ]
    async with engine.begin() as conn:
        for table, col, stmt in column_migrations:
            try:
                await conn.execute(text(stmt))
                print(f"  OK   {table}.{col}")
            except Exception as exc:
                print(f"  SKIP {table}.{col}  ({exc})")

    # ------------------------------------------------------------------ #
    # 3. Seed reference + auth data                                        #
    # ------------------------------------------------------------------ #
    print("\n[3/3] Seeding reference data")

    ref_seeds: list[tuple[str, str, list, str, object]] = [
        (
            "ref_countries", "alpha2", ISO_COUNTRIES,
            "INSERT INTO ref_countries (alpha2, alpha3, name) "
            "VALUES (:a2, :a3, :n) ON CONFLICT (alpha2) DO NOTHING",
            lambda r: {"a2": r[0], "a3": r[1], "n": r[2]},
        ),
        (
            "ref_currencies", "code", ISO_CURRENCIES,
            "INSERT INTO ref_currencies (code, numeric, name, decimals) "
            "VALUES (:c, :n, :nm, :d) ON CONFLICT (code) DO NOTHING",
            lambda r: {"c": r[0], "n": r[1], "nm": r[2], "d": r[3]},
        ),
        (
            "ref_languages", "alpha2", ISO_LANGUAGES,
            "INSERT INTO ref_languages (alpha2, alpha3, name) "
            "VALUES (:a2, :a3, :n) ON CONFLICT (alpha2) DO NOTHING",
            lambda r: {"a2": r[0], "a3": r[1], "n": r[2]},
        ),
        (
            "ref_timezones", "name", ISO_TIMEZONES,
            "INSERT INTO ref_timezones (name, utc_region) "
            "VALUES (:n, :r) ON CONFLICT (name) DO NOTHING",
            lambda r: {"n": r[0], "r": r[1]},
        ),
        (
            "ref_regions", "code", ISO_REGIONS,
            "INSERT INTO ref_regions (code, country, name, category) "
            "VALUES (:code, :country, :name, :category) ON CONFLICT (code) DO NOTHING",
            lambda r: {"code": r[0], "country": r[1], "name": r[2], "category": r[3]},
        ),
    ]

    async with Session() as db:
        for table, _pk, rows, stmt, params_fn in ref_seeds:
            before = await db.scalar(text(f"SELECT COUNT(*) FROM {table}"))
            for row in rows:
                await db.execute(text(stmt), params_fn(row))
            await db.commit()
            after = await db.scalar(text(f"SELECT COUNT(*) FROM {table}"))
            delta = after - before
            status = f"+{delta} inserted" if delta else "already complete"
            print(f"  {table:<22} {after:>5} rows  ({status})")

        # Sysadmin user
        result = await db.execute(select(User).where(User.email == SEEDED_SYSADMIN_EMAIL))
        if result.scalar_one_or_none() is None:
            db.add(User(email=SEEDED_SYSADMIN_EMAIL, role=ROLE_SYSADMIN, is_active=True))
            await db.commit()
            print(f"  sysadmin               seeded  ({SEEDED_SYSADMIN_EMAIL})")
        else:
            print(f"  sysadmin               already exists")

    await engine.dispose()
    print("\nDeployment complete.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deploy dqt database schema and reference data (idempotent)",
    )
    parser.add_argument("--url", metavar="DATABASE_URL", help="Override DATABASE_URL")
    args = parser.parse_args()
    asyncio.run(deploy(args.url))


if __name__ == "__main__":
    main()
