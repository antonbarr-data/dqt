"""Check schedule CRUD -- create, list, update, delete platform-wide check schedules."""
from __future__ import annotations

import calendar
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from dqt_server.db.engine import get_db
from dqt_server.models.core import CheckRun, CheckSchedule

router = APIRouter(prefix="/api/v1", tags=["schedules"])


def compute_next_run(
    cadence: str,
    run_hour: int,
    run_minute: int,
    days_of_week: list[int],
    day_of_month: int,
    from_dt: datetime,
) -> datetime:
    """Return the next scheduled datetime strictly after from_dt."""
    base = from_dt.replace(second=0, microsecond=0)

    if cadence == "hourly":
        candidate = base.replace(minute=run_minute, second=0, microsecond=0)
        if candidate <= base:
            candidate += timedelta(hours=1)
        return candidate

    if cadence == "daily":
        candidate = base.replace(hour=run_hour, minute=run_minute, second=0, microsecond=0)
        if candidate <= base:
            candidate += timedelta(days=1)
        return candidate

    if cadence == "weekly":
        active = days_of_week if days_of_week else list(range(7))
        candidate = base.replace(hour=run_hour, minute=run_minute, second=0, microsecond=0)
        for _ in range(8):
            if candidate.weekday() in active and candidate > base:
                return candidate
            candidate += timedelta(days=1)
        return candidate

    if cadence == "monthly":
        year, month = base.year, base.month
        for _ in range(13):
            max_day = calendar.monthrange(year, month)[1]
            dom = min(day_of_month, max_day)
            candidate = base.replace(
                year=year, month=month, day=dom,
                hour=run_hour, minute=run_minute, second=0, microsecond=0,
            )
            if candidate > base:
                return candidate
            month += 1
            if month > 12:
                month, year = 1, year + 1

    return base + timedelta(hours=1)


def _to_dict(s: CheckSchedule) -> dict[str, Any]:
    return {
        "id": s.id,
        "cadence": s.cadence,
        "run_hour": s.run_hour,
        "run_minute": s.run_minute,
        "days_of_week": s.days_of_week or [],
        "day_of_month": s.day_of_month,
        "enabled": s.enabled,
        "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
        "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


class ScheduleCreate(BaseModel):
    cadence: str  # hourly | daily | weekly | monthly
    run_hour: int = 0
    run_minute: int = 0
    days_of_week: list[int] = []
    day_of_month: int = 1


class SchedulePatch(BaseModel):
    enabled: bool


@router.get("/schedules")
async def list_schedules(db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(CheckSchedule).order_by(CheckSchedule.id))
    schedules = result.scalars().all()

    last_run_q = await db.execute(
        select(CheckRun.ran_at).order_by(desc(CheckRun.ran_at)).limit(1)
    )
    last_run_row = last_run_q.first()
    last_run_at = last_run_row[0].isoformat() if last_run_row else None

    return {
        "schedules": [_to_dict(s) for s in schedules],
        "last_run_at": last_run_at,
    }


@router.post("/schedules", status_code=201)
async def create_schedule(
    body: ScheduleCreate, db: AsyncSession = Depends(get_db)
) -> dict:
    if body.cadence not in ("hourly", "daily", "weekly", "monthly"):
        raise HTTPException(400, detail=f"Invalid cadence: {body.cadence}")

    now = datetime.now(timezone.utc)
    next_run = compute_next_run(
        body.cadence, body.run_hour, body.run_minute,
        body.days_of_week, body.day_of_month, now,
    )
    schedule = CheckSchedule(
        cadence=body.cadence,
        run_hour=body.run_hour,
        run_minute=body.run_minute,
        days_of_week=body.days_of_week,
        day_of_month=body.day_of_month,
        enabled=True,
        next_run_at=next_run,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return _to_dict(schedule)


@router.patch("/schedules/{schedule_id}")
async def patch_schedule(
    schedule_id: int, body: SchedulePatch, db: AsyncSession = Depends(get_db)
) -> dict:
    schedule = await db.get(CheckSchedule, schedule_id)
    if schedule is None:
        raise HTTPException(404, detail=f"Schedule {schedule_id} not found")
    schedule.enabled = body.enabled
    if body.enabled and schedule.next_run_at is None:
        schedule.next_run_at = compute_next_run(
            schedule.cadence, schedule.run_hour, schedule.run_minute,
            schedule.days_of_week or [], schedule.day_of_month, datetime.now(timezone.utc),
        )
    await db.commit()
    await db.refresh(schedule)
    return _to_dict(schedule)


@router.delete("/schedules/{schedule_id}", status_code=204)
async def delete_schedule(schedule_id: int, db: AsyncSession = Depends(get_db)):
    from fastapi.responses import Response
    schedule = await db.get(CheckSchedule, schedule_id)
    if schedule is None:
        raise HTTPException(404, detail=f"Schedule {schedule_id} not found")
    await db.delete(schedule)
    await db.commit()
    return Response(status_code=204)
