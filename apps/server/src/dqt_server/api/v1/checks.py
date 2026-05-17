"""Column-level check CRUD -- attach, list, update, delete check definitions."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1", tags=["checks"])


@dataclass
class CheckDefinition:
    id: str
    dataset_id: str
    column: str
    detector_slug: str
    params: dict[str, Any]
    rationale: str
    created_at: str
    updated_at: str


class _CheckStore:
    def __init__(self) -> None:
        self._checks: dict[str, CheckDefinition] = {}

    def list_for_column(self, dataset_id: str, column: str) -> list[CheckDefinition]:
        return [c for c in self._checks.values()
                if c.dataset_id == dataset_id and c.column == column]

    def get(self, check_id: str) -> CheckDefinition | None:
        return self._checks.get(check_id)

    def create(self, dataset_id: str, column: str, detector_slug: str,
               params: dict, rationale: str) -> CheckDefinition:
        now = datetime.now(timezone.utc).isoformat()
        check = CheckDefinition(
            id=str(uuid.uuid4())[:8],
            dataset_id=dataset_id,
            column=column,
            detector_slug=detector_slug,
            params=params,
            rationale=rationale,
            created_at=now,
            updated_at=now,
        )
        self._checks[check.id] = check
        return check

    def update(self, check_id: str, params: dict | None, rationale: str | None) -> CheckDefinition:
        c = self._checks.get(check_id)
        if c is None:
            raise KeyError(check_id)
        if params is not None:
            c.params = params
        if rationale is not None:
            c.rationale = rationale
        c.updated_at = datetime.now(timezone.utc).isoformat()
        return c

    def delete(self, check_id: str) -> bool:
        return self._checks.pop(check_id, None) is not None


_store = _CheckStore()


def _to_dict(c: CheckDefinition) -> dict:
    return {
        "id": c.id,
        "dataset_id": c.dataset_id,
        "column": c.column,
        "detector_slug": c.detector_slug,
        "params": c.params,
        "rationale": c.rationale,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
    }


class CheckCreate(BaseModel):
    detector_slug: str
    params: dict[str, Any] = field(default_factory=dict)
    rationale: str = ""


class CheckUpdate(BaseModel):
    params: dict[str, Any] | None = None
    rationale: str | None = None


@router.get("/datasets/{dataset_id}/columns/{column}/checks")
async def list_column_checks(dataset_id: str, column: str) -> list[dict]:
    return [_to_dict(c) for c in _store.list_for_column(dataset_id, column)]


@router.post("/datasets/{dataset_id}/columns/{column}/checks", status_code=201)
async def create_column_check(dataset_id: str, column: str, body: CheckCreate) -> dict:
    check = _store.create(
        dataset_id=dataset_id,
        column=column,
        detector_slug=body.detector_slug,
        params=body.params,
        rationale=body.rationale,
    )
    return _to_dict(check)


@router.put("/checks/{check_id}")
async def update_check(check_id: str, body: CheckUpdate) -> dict:
    try:
        check = _store.update(check_id, params=body.params, rationale=body.rationale)
    except KeyError:
        raise HTTPException(404, detail=f"Check '{check_id}' not found")
    return _to_dict(check)


@router.delete("/checks/{check_id}")
async def delete_check(check_id: str) -> dict:
    if not _store.delete(check_id):
        raise HTTPException(404, detail=f"Check '{check_id}' not found")
    return {"id": check_id, "deleted": True}
