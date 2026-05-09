from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

_raw = os.environ.get("DATABASE_URL", "")
DATABASE_URL = (
    _raw.replace("postgresql://", "postgresql+asyncpg://", 1)
        .replace("postgres://", "postgresql+asyncpg://", 1)
) if _raw else ""


def _make_engine():
    if not DATABASE_URL:
        return None
    return create_async_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=10)


engine = _make_engine()
AsyncSessionLocal: async_sessionmaker | None = (
    async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession) if engine else None
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:  # type: ignore[return]
    if AsyncSessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured")
    async with AsyncSessionLocal() as session:
        yield session
