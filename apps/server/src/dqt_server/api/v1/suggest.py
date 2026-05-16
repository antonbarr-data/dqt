"""Column-level check suggestion endpoint."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from dqt_server.db.engine import get_db
from dqt_server.models.gigler import Dataset
from dqt_server.gigler_service import gigler_service
from dqt.checks.suggest import ColumnProfile, suggest_checks_for_column

router = APIRouter(prefix="/api/v1", tags=["suggest"])


def _build_profile(dataset_id: str, column: str, profile_data: dict) -> ColumnProfile:
    name = column
    data_type = profile_data.get("data_type", "text")
    null_fraction = float(profile_data.get("null_fraction", 0.0))
    distinct_count = int(profile_data.get("distinct_count", 0))
    sample_values = [str(v) for v in profile_data.get("sample_values", [])[:10]]
    min_value = profile_data.get("min_value")
    max_value = profile_data.get("max_value")

    name_lower = name.lower()
    is_likely_pk = (
        name_lower in ("id", f"{dataset_id}_id", "pk")
        or (name_lower.endswith("_id") and distinct_count > 1000 and null_fraction == 0.0)
    )
    is_likely_fk = name_lower.endswith("_id") and not is_likely_pk
    is_likely_enum = 0 < distinct_count < 50
    is_likely_email = "email" in name_lower or any("@" in v for v in sample_values[:5])
    is_likely_timestamp = (
        any(t in data_type.lower() for t in ("timestamp", "datetime", "date", "time"))
        or any(k in name_lower for k in ("_at", "_date", "_time", "timestamp", "created", "updated"))
    )
    is_likely_currency = any(
        k in name_lower for k in ("amount", "price", "revenue", "cost", "fee", "total")
    )
    is_likely_country = (
        name_lower in ("country", "country_code", "country_iso")
        or (0 < distinct_count < 300 and all(len(v) == 2 for v in sample_values[:5] if v))
    )

    return ColumnProfile(
        name=name,
        data_type=data_type,
        null_fraction=null_fraction,
        distinct_count=distinct_count,
        sample_values=sample_values,
        min_value=min_value,
        max_value=max_value,
        is_likely_pk=is_likely_pk,
        is_likely_fk=is_likely_fk,
        is_likely_enum=is_likely_enum,
        is_likely_email=is_likely_email,
        is_likely_timestamp=is_likely_timestamp,
        is_likely_currency=is_likely_currency,
        is_likely_country=is_likely_country,
        sample_size_used=int(profile_data.get("sample_size", 0)),
    )


@router.get("/datasets/{dataset_id}/columns/{column}/suggest")
async def suggest_checks(
    dataset_id: str,
    column: str,
    use_llm: bool = False,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return ranked check suggestions for a column, sorted by confidence descending."""
    d = await db.get(Dataset, dataset_id)
    if d is None:
        raise HTTPException(404, detail=f"Dataset '{dataset_id}' not found")

    loop = asyncio.get_event_loop()
    try:
        profile_data = await loop.run_in_executor(
            None, gigler_service._profile_column_sync, dataset_id, column
        )
    except Exception:
        profile_data = {}

    profile = _build_profile(dataset_id, column, profile_data)
    suggestions = suggest_checks_for_column(profile, use_llm=use_llm)

    return [
        {
            "detector_slug": s.detector_slug,
            "params": s.params,
            "rationale": s.rationale,
            "confidence": round(s.confidence, 3),
        }
        for s in suggestions
    ]
