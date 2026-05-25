from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path


def _load_dotenv() -> None:
    """Load .env from repo root if present (dev convenience -- no-op in prod)."""
    candidate = Path(__file__).parents[4] / ".env"
    if not candidate.exists():
        return
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


_load_dotenv()

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from dqt_server.auth.models import ROLE_SYSADMIN, User
from dqt_server.auth.router import router as auth_router
from dqt_server.auth.service import SEEDED_SYSADMIN_EMAIL
from dqt_server.dashboard import router as dashboard_router
from dqt_server.db.engine import AsyncSessionLocal, Base, engine
from dqt_server.models import ref_data as _ref_models  # noqa: F401 -- registers ORM models with Base
from dqt_server.ref_data import ISO_COUNTRIES, ISO_CURRENCIES
from dqt_server.ref_data_languages import ISO_LANGUAGES
from dqt_server.ref_data_timezones import ISO_TIMEZONES
from dqt_server.ref_data_regions import ISO_REGIONS

log = structlog.get_logger(__name__)


async def _setup_db() -> None:
    if engine is None:
        log.warning("DATABASE_URL not set -- skipping DB setup")
        return
    async with engine.begin() as conn:
        # Creates all tables defined via SQLAlchemy Base (including ref_* tables)
        await conn.run_sync(Base.metadata.create_all)
        # Add columns to existing tables that predate this column
        for stmt in [
            "ALTER TABLE sources ADD COLUMN IF NOT EXISTS password VARCHAR",
            "ALTER TABLE sources ADD COLUMN IF NOT EXISTS secure BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE column_checks ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT TRUE",
            "ALTER TABLE metric_definitions ADD COLUMN IF NOT EXISTS source_id VARCHAR",
            "ALTER TABLE metric_definitions ADD COLUMN IF NOT EXISTS column_name VARCHAR",
            "ALTER TABLE metric_definitions ADD COLUMN IF NOT EXISTS warn_threshold DOUBLE PRECISION",
            "ALTER TABLE metric_definitions ADD COLUMN IF NOT EXISTS fail_threshold DOUBLE PRECISION",
        ]:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass
    # Seed reference data (skip if already present)
    async with AsyncSessionLocal() as db:
        count = await db.scalar(text("SELECT COUNT(*) FROM ref_countries"))
        if not count:
            for alpha2, alpha3, name in ISO_COUNTRIES:
                await db.execute(
                    text(
                        "INSERT INTO ref_countries (alpha2, alpha3, name) VALUES (:a2, :a3, :n) "
                        "ON CONFLICT (alpha2) DO NOTHING"
                    ),
                    {"a2": alpha2, "a3": alpha3, "n": name},
                )
            await db.commit()
            log.info("seeded_ref_countries", count=len(ISO_COUNTRIES))

        count = await db.scalar(text("SELECT COUNT(*) FROM ref_currencies"))
        if not count:
            for code, numeric, name, decimals in ISO_CURRENCIES:
                await db.execute(
                    text(
                        "INSERT INTO ref_currencies (code, numeric, name, decimals) "
                        "VALUES (:c, :n, :nm, :d) ON CONFLICT (code) DO NOTHING"
                    ),
                    {"c": code, "n": numeric, "nm": name, "d": decimals},
                )
            await db.commit()
            log.info("seeded_ref_currencies", count=len(ISO_CURRENCIES))

        count = await db.scalar(text("SELECT COUNT(*) FROM ref_languages"))
        if not count:
            for alpha2, alpha3, name in ISO_LANGUAGES:
                await db.execute(
                    text(
                        "INSERT INTO ref_languages (alpha2, alpha3, name) VALUES (:a2, :a3, :n) "
                        "ON CONFLICT (alpha2) DO NOTHING"
                    ),
                    {"a2": alpha2, "a3": alpha3, "n": name},
                )
            await db.commit()
            log.info("seeded_ref_languages", count=len(ISO_LANGUAGES))

        count = await db.scalar(text("SELECT COUNT(*) FROM ref_timezones"))
        if not count:
            for name, utc_region in ISO_TIMEZONES:
                await db.execute(
                    text(
                        "INSERT INTO ref_timezones (name, utc_region) VALUES (:n, :r) "
                        "ON CONFLICT (name) DO NOTHING"
                    ),
                    {"n": name, "r": utc_region},
                )
            await db.commit()
            log.info("seeded_ref_timezones", count=len(ISO_TIMEZONES))

        count = await db.scalar(text("SELECT COUNT(*) FROM ref_regions"))
        if not count:
            for code, country, name, category in ISO_REGIONS:
                await db.execute(
                    text(
                        "INSERT INTO ref_regions (code, country, name, category) "
                        "VALUES (:code, :country, :name, :category) ON CONFLICT (code) DO NOTHING"
                    ),
                    {"code": code, "country": country, "name": name, "category": category},
                )
            await db.commit()
            log.info("seeded_ref_regions", count=len(ISO_REGIONS))

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == SEEDED_SYSADMIN_EMAIL))
        if result.scalar_one_or_none() is None:
            db.add(User(email=SEEDED_SYSADMIN_EMAIL, role=ROLE_SYSADMIN, is_active=True))
            await db.commit()
            log.info("seeded_super_admin", email=SEEDED_SYSADMIN_EMAIL)


async def _scheduler_loop() -> None:
    """Every 60 s: fire check_runner.refresh() for any due enabled schedules."""
    from sqlalchemy import select as _select
    from dqt_server.api.v1.schedules import compute_next_run
    from dqt_server.check_runner import check_runner
    from dqt_server.models.core import CheckSchedule

    while True:
        await asyncio.sleep(60)
        if AsyncSessionLocal is None:
            continue
        try:
            now = datetime.now(timezone.utc)
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    _select(CheckSchedule).where(
                        CheckSchedule.enabled.is_(True),
                        CheckSchedule.next_run_at <= now,
                    )
                )
                due = result.scalars().all()
                if due:
                    asyncio.create_task(check_runner.refresh())
                    for s in due:
                        s.last_run_at = now
                        s.next_run_at = compute_next_run(
                            s.cadence, s.run_hour, s.run_minute,
                            list(s.days_of_week or []), s.day_of_month or 1, now,
                        )
                    await db.commit()
                    log.info("scheduled_refresh_fired", count=len(due))
        except Exception as exc:
            log.error("scheduler_loop_error", error=str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _setup_db()
    sched_task = asyncio.create_task(_scheduler_loop())
    try:
        yield
    finally:
        sched_task.cancel()


app = FastAPI(title="dqt API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from dqt_server.api.v1.sources import router as sources_router
from dqt_server.api.v1.suggest import router as suggest_router
from dqt_server.api.v1.search import router as search_router
from dqt_server.api.v1.insights import router as insights_router
from dqt_server.api.v1.feed import router as feed_router
from dqt_server.api.v1.ask import router as ask_router
from dqt_server.api.v1.subscriptions import router as subscriptions_router
from dqt_server.api.v1.trigger import router as trigger_router
from dqt_server.api.v1.lineage import router as lineage_router
from dqt_server.api.v1.causal_review import router as causal_review_router
from dqt_server.api.v1.checks import router as checks_router
from dqt_server.api.v1.detectors import router as detectors_router
from dqt_server.api.v1.causal_compute import router as causal_compute_router
from dqt_server.api.v1.schedules import router as schedules_router

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(sources_router)
app.include_router(suggest_router)
app.include_router(search_router)   # BEFORE insights -- /metrics/search before /metrics/{fqn:path}
app.include_router(insights_router)
app.include_router(feed_router)
app.include_router(ask_router)
app.include_router(subscriptions_router)
app.include_router(trigger_router)
app.include_router(lineage_router)
app.include_router(causal_review_router)
app.include_router(checks_router)
app.include_router(detectors_router)
app.include_router(causal_compute_router)
app.include_router(schedules_router)


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok", "service": "dqt-server"}


@app.get("/api/v1/ping", tags=["ops"])
def ping() -> dict:
    return {"pong": True}
