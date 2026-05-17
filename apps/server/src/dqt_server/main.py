from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from dqt_server.auth.models import ROLE_SYSADMIN, User
from dqt_server.auth.router import router as auth_router
from dqt_server.auth.service import SEEDED_SYSADMIN_EMAIL
from dqt_server.dashboard import router as dashboard_router
from dqt_server.db.engine import AsyncSessionLocal, Base, engine

log = structlog.get_logger(__name__)


async def _setup_db() -> None:
    if engine is None:
        log.warning("DATABASE_URL not set — skipping DB setup")
        return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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

from dqt_server.api.v1.suggest import router as suggest_router
from dqt_server.api.v1.search import router as search_router
from dqt_server.api.v1.insights import router as insights_router
from dqt_server.api.v1.feed import router as feed_router
from dqt_server.api.v1.ask import router as ask_router

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(suggest_router)
app.include_router(search_router)   # BEFORE insights -- /metrics/search before /metrics/{fqn:path}
app.include_router(insights_router)
app.include_router(feed_router)
app.include_router(ask_router)


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok", "service": "dqt-server"}


@app.get("/api/v1/ping", tags=["ops"])
def ping() -> dict:
    return {"pong": True}
