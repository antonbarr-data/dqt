from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from dqt_server.auth.models import ROLE_SYSADMIN, User
from dqt_server.auth.router import router as auth_router
from dqt_server.auth.service import SEEDED_SYSADMIN_EMAIL
from dqt_server.dashboard import router as dashboard_router
from dqt_server.db.engine import AsyncSessionLocal, Base, engine
from dqt_server.ref_data import CREATE_REF_TABLES_SQL, ISO_COUNTRIES, ISO_CURRENCIES

log = structlog.get_logger(__name__)


async def _setup_db() -> None:
    if engine is None:
        log.warning("DATABASE_URL not set -- skipping DB setup")
        return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Add columns to existing tables that predate this column
        for stmt in [
            "ALTER TABLE sources ADD COLUMN IF NOT EXISTS password VARCHAR",
            "ALTER TABLE sources ADD COLUMN IF NOT EXISTS secure BOOLEAN NOT NULL DEFAULT FALSE",
        ]:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass
        # Reference tables (idempotent)
        for stmt in CREATE_REF_TABLES_SQL.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                try:
                    await conn.execute(text(stmt))
                except Exception:
                    pass
    # Seed reference data (upsert, skip if present)
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

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == SEEDED_SYSADMIN_EMAIL))
        if result.scalar_one_or_none() is None:
            db.add(User(email=SEEDED_SYSADMIN_EMAIL, role=ROLE_SYSADMIN, is_active=True))
            await db.commit()
            log.info("seeded_super_admin", email=SEEDED_SYSADMIN_EMAIL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _setup_db()
    yield


app = FastAPI(title="dqt API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from dqt_server.api.v1.gigler import router as gigler_router
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

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(gigler_router)
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


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok", "service": "dqt-server"}


@app.get("/api/v1/ping", tags=["ops"])
def ping() -> dict:
    return {"pong": True}
