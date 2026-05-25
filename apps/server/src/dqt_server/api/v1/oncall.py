"""On-call schedule management.

Each User marked oncall_eligible gets a row in oncall_shifts mapping them to the
days of the week (0=Mon..6=Sun) they cover. When the eligible roster changes, days
are redistributed evenly across all eligible active users.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from dqt_server.auth.models import User
from dqt_server.db.engine import get_db
from dqt_server.models.core import OncallShift

router = APIRouter(prefix="/api/v1/oncall", tags=["oncall"])

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _parse_days(raw: str) -> list[int]:
    return [int(d) for d in raw.split(",") if d.strip().isdigit()]


def _fmt_days(days: list[int]) -> str:
    return ",".join(str(d) for d in sorted(set(days)))


async def redistribute_oncall_days(db: AsyncSession) -> None:
    """Re-assign all 7 days evenly across oncall_eligible active users (sorted by created_at)."""
    result = await db.execute(
        select(User)
        .where(User.oncall_eligible.is_(True), User.is_active.is_(True))
        .order_by(User.created_at)
    )
    eligible = result.scalars().all()

    await db.execute(sa_delete(OncallShift))

    if not eligible:
        await db.commit()
        return

    assignments: dict[str, list[int]] = {str(u.id): [] for u in eligible}
    for day in range(7):
        uid = str(eligible[day % len(eligible)].id)
        assignments[uid].append(day)

    for uid, days in assignments.items():
        db.add(OncallShift(user_id=uid, days_of_week=_fmt_days(days)))

    await db.commit()


async def _shifts_with_users(db: AsyncSession) -> list[dict]:
    shifts = (await db.execute(select(OncallShift))).scalars().all()
    out = []
    for s in shifts:
        user = await db.get(User, s.user_id)
        out.append({
            "user_id": s.user_id,
            "email": user.email if user else s.user_id,
            "name": user.name if user else None,
            "days_of_week": _parse_days(s.days_of_week),
        })
    return sorted(out, key=lambda x: min(x["days_of_week"]) if x["days_of_week"] else 99)


@router.get("/status")
async def get_oncall_status(db: AsyncSession = Depends(get_db)) -> dict:
    """Return current on-call user, upcoming on-call, and full weekly schedule."""
    schedule = await _shifts_with_users(db)
    today = datetime.now(timezone.utc).weekday()  # 0=Mon..6=Sun

    current = next((s for s in schedule if today in s["days_of_week"]), None)

    upcoming = None
    if not current:
        for offset in range(1, 7):
            candidate_day = (today + offset) % 7
            match = next((s for s in schedule if candidate_day in s["days_of_week"]), None)
            if match:
                upcoming = {**match, "next_day": DAY_NAMES[candidate_day], "days_until": offset}
                break

    return {
        "current_oncall": {**current, "today": DAY_NAMES[today]} if current else None,
        "upcoming_oncall": upcoming,
        "schedule": schedule,
        "today_name": DAY_NAMES[today],
    }


class ShiftUpdate(BaseModel):
    days_of_week: list[int]


@router.put("/shifts/{user_id}")
async def update_shift(
    user_id: str,
    body: ShiftUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Manually assign specific days to a user (overrides auto-distribution)."""
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    if not user.oncall_eligible:
        raise HTTPException(400, "User is not oncall_eligible")

    result = await db.execute(select(OncallShift).where(OncallShift.user_id == user_id))
    shift = result.scalar_one_or_none()
    days = sorted(set(d for d in body.days_of_week if 0 <= d <= 6))
    if shift:
        shift.days_of_week = _fmt_days(days)
    else:
        db.add(OncallShift(user_id=user_id, days_of_week=_fmt_days(days)))
    await db.commit()
    return {"user_id": user_id, "days_of_week": days}


@router.post("/redistribute")
async def trigger_redistribute(db: AsyncSession = Depends(get_db)) -> dict:
    """Manually re-run the even redistribution across all eligible users."""
    await redistribute_oncall_days(db)
    schedule = await _shifts_with_users(db)
    return {"schedule": schedule}
