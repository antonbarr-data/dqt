"""Column-level check CRUD -- attach, list, update, delete check definitions."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete as sa_delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from dqt_server.db.engine import get_db
from dqt_server.models.core import CheckRun, ColumnCheck

router = APIRouter(prefix="/api/v1", tags=["checks"])


def _to_dict(c: ColumnCheck) -> dict:
    return {
        "id": c.id,
        "dataset_id": c.dataset_id,
        "column": c.column_name,
        "detector_slug": c.detector_slug,
        "params": c.params,
        "rationale": c.rationale,
        "enabled": c.enabled,
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
    enabled: bool | None = None


class CheckBatchUpdate(BaseModel):
    ids: list[str]
    enabled: bool


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
    if body.enabled is not None:
        check.enabled = body.enabled
    check.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(check)
    return _to_dict(check)


@router.patch("/checks/batch")
async def batch_update_checks(
    body: CheckBatchUpdate, db: AsyncSession = Depends(get_db)
) -> dict:
    from sqlalchemy import update as sa_update
    await db.execute(
        sa_update(ColumnCheck)
        .where(ColumnCheck.id.in_(body.ids))
        .values(enabled=body.enabled, updated_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"updated": len(body.ids), "enabled": body.enabled}


@router.delete("/datasets/{dataset_id}/columns/{column}", status_code=204)
async def delete_column(
    dataset_id: str, column: str, db: AsyncSession = Depends(get_db)
) -> None:
    from sqlalchemy import delete as sa_delete
    await db.execute(
        sa_delete(ColumnCheck).where(
            ColumnCheck.dataset_id == dataset_id,
            ColumnCheck.column_name == column,
        )
    )
    await db.commit()



@router.post("/checks/{check_id}/run")
async def run_single_check(check_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    check = await db.get(ColumnCheck, check_id)
    if check is None:
        raise HTTPException(404, detail=f"Check '{check_id}' not found")
    from dqt_server.check_runner import check_runner
    result = await check_runner.run_single(check_id)
    if "error" in result:
        raise HTTPException(500, detail=result["error"])
    return result


@router.delete("/checks/{check_id}")
async def delete_check(check_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    check = await db.get(ColumnCheck, check_id)
    if check is None:
        raise HTTPException(404, detail=f"Check '{check_id}' not found")
    await db.delete(check)
    await db.commit()
    return {"id": check_id, "deleted": True}


class CheckBatchDelete(BaseModel):
    ids: list[str]


@router.delete("/checks")
async def delete_all_checks(db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(sa_delete(ColumnCheck))
    await db.commit()
    return {"deleted": result.rowcount or 0}


@router.post("/checks/batch-delete")
async def batch_delete_checks(body: CheckBatchDelete, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(sa_delete(ColumnCheck).where(ColumnCheck.id.in_(body.ids)))
    await db.commit()
    return {"deleted": result.rowcount or 0}


class ImportChecksBody(BaseModel):
    yaml_content: str
    mode: Literal["merge", "replace"]


@router.post("/checks/import")
async def import_checks(body: ImportChecksBody, db: AsyncSession = Depends(get_db)) -> dict:
    import yaml as _yaml

    parsed: list[dict] = []
    errors: list[str] = []
    try:
        docs = list(_yaml.safe_load_all(body.yaml_content))
    except Exception as exc:
        raise HTTPException(400, detail=f"YAML parse error: {exc}")

    for i, doc in enumerate(docs):
        if not doc or not isinstance(doc, dict):
            continue
        check_slug = doc.get("check")
        table = doc.get("table")
        if not check_slug or not table:
            errors.append(f"document {i + 1}: missing 'check' or 'table' field")
            continue
        parsed.append({
            "dataset_id": str(table),
            "column_name": str(doc["column"]) if doc.get("column") else "(table)",
            "detector_slug": str(check_slug),
            "params": doc.get("params") or {},
            "rationale": str(doc.get("rationale") or ""),
            "enabled": bool(doc.get("enabled", True)),
        })

    # Deduplicate within the imported batch
    seen: set[tuple] = set()
    deduped: list[dict] = []
    for p in parsed:
        key = (p["dataset_id"], p["column_name"], p["detector_slug"])
        if key not in seen:
            seen.add(key)
            deduped.append(p)

    deleted = 0
    if body.mode == "replace":
        result = await db.execute(sa_delete(ColumnCheck))
        deleted = result.rowcount or 0

    existing_q = await db.execute(select(ColumnCheck))
    existing_keys = {
        (c.dataset_id, c.column_name, c.detector_slug)
        for c in existing_q.scalars().all()
    }

    now = datetime.now(timezone.utc)
    added = 0
    skipped = 0
    for p in deduped:
        key = (p["dataset_id"], p["column_name"], p["detector_slug"])
        if key in existing_keys:
            skipped += 1
            continue
        db.add(ColumnCheck(
            id=str(uuid.uuid4())[:8],
            dataset_id=p["dataset_id"],
            column_name=p["column_name"],
            detector_slug=p["detector_slug"],
            params=p["params"],
            rationale=p["rationale"],
            enabled=p["enabled"],
            created_at=now,
            updated_at=now,
        ))
        existing_keys.add(key)
        added += 1

    await db.commit()
    return {"added": added, "skipped": skipped, "deleted": deleted, "errors": errors}


_VERDICT_SCORE = {"pass": 100, "warn": 60, "fail": 0}


@router.get("/score")
async def get_platform_score(db: AsyncSession = Depends(get_db)) -> dict:
    checks_q = await db.execute(select(ColumnCheck))
    checks = checks_q.scalars().all()

    results = []
    for c in checks:
        run_q = await db.execute(
            select(CheckRun)
            .where(
                CheckRun.dataset_id == c.dataset_id,
                CheckRun.column_name == c.column_name,
                CheckRun.detector_slug == c.detector_slug,
            )
            .order_by(desc(CheckRun.ran_at))
            .limit(1)
        )
        run = run_q.scalars().first()
        if run is None:
            continue
        verdict = run.verdict or "fail"
        results.append({
            "id": c.id,
            "dataset_id": c.dataset_id,
            "column": c.column_name,
            "detector_slug": c.detector_slug,
            "score": _VERDICT_SCORE.get(verdict, 0),
            "verdict": verdict,
            "ran_at": run.ran_at.isoformat(),
        })

    platform_score = (
        round(sum(r["score"] for r in results) / len(results))
        if results else None
    )
    return {"platform_score": platform_score, "checks": results}
