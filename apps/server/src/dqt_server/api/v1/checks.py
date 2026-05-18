"""Column-level check CRUD -- attach, list, update, delete check definitions."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dqt_server.db.engine import get_db
from dqt_server.models.core import ColumnCheck

router = APIRouter(prefix="/api/v1", tags=["checks"])


def _to_dict(c: ColumnCheck) -> dict:
    return {
        "id": c.id,
        "dataset_id": c.dataset_id,
        "column": c.column_name,
        "detector_slug": c.detector_slug,
        "params": c.params,
        "rationale": c.rationale,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


class CheckCreate(BaseModel):
    detector_slug: str
    params: dict[str, Any] = {}
    rationale: str = ""


class CheckUpdate(BaseModel):
    params: dict[str, Any] | None = None
    rationale: str | None = None


@router.get("/datasets/{dataset_id}/columns/{column}/checks")
async def list_column_checks(
    dataset_id: str, column: str, db: AsyncSession = Depends(get_db)
) -> list[dict]:
    result = await db.execute(
        select(ColumnCheck).where(
            ColumnCheck.dataset_id == dataset_id,
            ColumnCheck.column_name == column,
        )
    )
    return [_to_dict(c) for c in result.scalars().all()]


@router.post("/datasets/{dataset_id}/columns/{column}/checks", status_code=201)
async def create_column_check(
    dataset_id: str, column: str, body: CheckCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    now = datetime.now(timezone.utc)
    check = ColumnCheck(
        id=str(uuid.uuid4())[:8],
        dataset_id=dataset_id,
        column_name=column,
        detector_slug=body.detector_slug,
        params=body.params,
        rationale=body.rationale,
        created_at=now,
        updated_at=now,
    )
    db.add(check)
    await db.commit()
    await db.refresh(check)
    return _to_dict(check)


@router.put("/checks/{check_id}")
async def update_check(
    check_id: str, body: CheckUpdate, db: AsyncSession = Depends(get_db)
) -> dict:
    check = await db.get(ColumnCheck, check_id)
    if check is None:
        raise HTTPException(404, detail=f"Check '{check_id}' not found")
    if body.params is not None:
        check.params = body.params
    if body.rationale is not None:
        check.rationale = body.rationale
    check.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(check)
    return _to_dict(check)


@router.delete("/checks/{check_id}")
async def delete_check(check_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    check = await db.get(ColumnCheck, check_id)
    if check is None:
        raise HTTPException(404, detail=f"Check '{check_id}' not found")
    await db.delete(check)
    await db.commit()
    return {"id": check_id, "deleted": True}
