"""REST API routes for Gigler ClickHouse data — sources, datasets, checks, incidents."""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone, timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dqt_server.db.engine import get_db
from dqt_server.gigler_service import GIGLER_SOURCE_ID, GIGLER_TABLES, gigler_service
from dqt_server.models.gigler import CheckRun, Dataset, Incident, Source

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["gigler"])


def _time_ago(dt: datetime | None) -> str:
    if dt is None:
        return "never"
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt
    secs = int(delta.total_seconds())
    if secs < 60:
        return f"{secs}s ago"
    if secs < 3600:
        return f"{secs // 60}m ago"
    if secs < 86400:
        return f"{secs // 3600}h ago"
    return f"{secs // 86400}d ago"


def _source_dict(s: Source) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "engine": s.engine,
        "endpoint": f"{s.host}:{s.port}/{s.db_name}",
        "host": s.host,
        "port": s.port,
        "tables": s.table_count,
        "status": s.status,
        "last_sync": _time_ago(s.last_synced_at),
    }


def _dataset_dict(d: Dataset) -> dict:
    return {
        "id": d.id,
        "source": d.source_id,
        "schema": d.schema_name,
        "row_count": d.row_count,
        "column_count": d.column_count,
        "check_count": d.check_count,
        "status": d.status,
        "last_run": _time_ago(d.last_run_at),
    }


def _run_dict(r: CheckRun) -> dict:
    return {
        "id": r.id,
        "dataset_id": r.dataset_id,
        "column": r.column_name,
        "detector": r.detector_slug,
        "score": r.score,
        "verdict": r.verdict,
        "message": r.plain_english,
        "details": r.details,
        "ran_at": r.ran_at.isoformat() if r.ran_at else None,
        "ran_at_ago": _time_ago(r.ran_at),
    }


def _incident_dict(i: Incident) -> dict:
    return {
        "id": i.id,
        "dataset_id": i.dataset_id,
        "column": i.column_name,
        "detector": i.detector_slug,
        "severity": i.severity,
        "message": i.message,
        "status": i.status,
        "opened_at": i.opened_at.isoformat() if i.opened_at else None,
        "opened_ago": _time_ago(i.opened_at),
        "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None,
    }


# ------------------------------------------------------------------
# Sources
# ------------------------------------------------------------------

@router.get("/sources")
async def list_sources(db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(select(Source).order_by(Source.name))
    return [_source_dict(s) for s in result.scalars().all()]


@router.get("/sources/{source_id}")
async def get_source(source_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    s = await db.get(Source, source_id)
    if s is None:
        raise HTTPException(404, detail=f"Source '{source_id}' not found")
    return _source_dict(s)


# ------------------------------------------------------------------
# Datasets
# ------------------------------------------------------------------

@router.get("/datasets")
async def list_datasets(db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(select(Dataset).order_by(Dataset.id))
    return [_dataset_dict(d) for d in result.scalars().all()]


@router.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    d = await db.get(Dataset, dataset_id)
    if d is None:
        raise HTTPException(404, detail=f"Dataset '{dataset_id}' not found")

    # Latest check run per column
    runs_q = await db.execute(
        select(CheckRun)
        .where(CheckRun.dataset_id == dataset_id)
        .order_by(desc(CheckRun.ran_at))
        .limit(200)
    )
    runs = runs_q.scalars().all()

    # Deduplicate to latest run per column
    seen: set[str | None] = set()
    latest_runs: list[CheckRun] = []
    for r in runs:
        key = r.column_name
        if key not in seen:
            seen.add(key)
            latest_runs.append(r)

    return {
        **_dataset_dict(d),
        "checks": [_run_dict(r) for r in latest_runs],
    }


# ------------------------------------------------------------------
# Checks
# ------------------------------------------------------------------

@router.get("/checks")
async def list_checks(
    dataset_id: str | None = None,
    verdict: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    q = select(CheckRun).order_by(desc(CheckRun.ran_at))
    if dataset_id:
        q = q.where(CheckRun.dataset_id == dataset_id)
    if verdict:
        q = q.where(CheckRun.verdict == verdict)

    # Return latest per (dataset, column) pair
    result = await db.execute(q.limit(1000))
    runs = result.scalars().all()

    seen: set[tuple] = set()
    deduped: list[CheckRun] = []
    for r in runs:
        key = (r.dataset_id, r.column_name, r.detector_slug)
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    return [_run_dict(r) for r in deduped]


@router.post("/checks/refresh")
async def refresh_checks() -> dict:
    """Trigger a non-blocking refresh of all ClickHouse checks."""
    asyncio.create_task(gigler_service.refresh())
    return {"status": "refresh_started"}


# ------------------------------------------------------------------
# Incidents
# ------------------------------------------------------------------

@router.get("/incidents")
async def list_incidents(
    status: str = "open",
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    q = (
        select(Incident)
        .where(Incident.status == status)
        .order_by(desc(Incident.opened_at))
        .limit(200)
    )
    result = await db.execute(q)
    return [_incident_dict(i) for i in result.scalars().all()]


@router.get("/datasets/{dataset_id}/columns/{column}/profile")
async def get_column_profile(
    dataset_id: str,
    column: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    d = await db.get(Dataset, dataset_id)
    if d is None:
        raise HTTPException(404, detail=f"Dataset '{dataset_id}' not found")
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, gigler_service._profile_column_sync, dataset_id, column
    )


@router.get("/incidents/{incident_id}")
async def get_incident(incident_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    i = await db.get(Incident, incident_id)
    if i is None:
        raise HTTPException(404, detail=f"Incident {incident_id} not found")
    return _incident_dict(i)


# ------------------------------------------------------------------
# Overview
# ------------------------------------------------------------------

@router.get("/overview")
async def overview(db: AsyncSession = Depends(get_db)) -> dict:
    open_count = await db.scalar(
        select(func.count()).where(Incident.status == "open")
    ) or 0
    dataset_count = await db.scalar(select(func.count()).select_from(Dataset)) or 0
    check_count = await db.scalar(select(func.count()).select_from(CheckRun)) or 0

    datasets_q = await db.execute(select(Dataset).order_by(Dataset.id))
    datasets = datasets_q.scalars().all()

    # Activity: latest 8 incidents
    activity_q = await db.execute(
        select(Incident).order_by(desc(Incident.opened_at)).limit(8)
    )
    activity = activity_q.scalars().all()

    activity_items = []
    for inc in activity:
        kind = inc.severity if inc.status == "open" else "pass"
        activity_items.append({
            "time": _time_ago(inc.opened_at),
            "text": inc.message,
            "kind": kind,
        })

    # If no real activity yet, add a placeholder
    if not activity_items:
        activity_items = [
            {"time": "just now", "text": "No incidents recorded yet", "kind": "info"}
        ]

    return {
        "kpis": {
            "open_incidents": open_count,
            "datasets_watched": dataset_count or len(GIGLER_TABLES),
            "checks_running": check_count,
            "auto_explained": 0,
        },
        "datasets": [{"id": d.id, "status": d.status} for d in datasets],
        "activity": activity_items,
    }
