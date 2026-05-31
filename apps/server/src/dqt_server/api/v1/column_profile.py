"""Column profile endpoints — stats cache, schema history, incidents."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from dqt_server.check_runner import _default_schema_for_source, _make_adapter
from dqt_server.db.engine import get_db
from dqt_server.models.core import (
    ColumnSchemaHistory,
    ColumnStatsCache,
    Dataset,
    Incident,
    Source,
)

log = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["column-profile"])


async def _get_source_for_dataset(dataset_id: str, db: AsyncSession) -> tuple[Dataset, Source]:
    d = await db.get(Dataset, dataset_id)
    if d is None:
        raise HTTPException(404, detail=f"Dataset '{dataset_id}' not found")
    s = await db.get(Source, d.source_id)
    if s is None:
        raise HTTPException(404, detail="Source not found")
    return d, s


def _row_to_dict(row: ColumnStatsCache) -> dict:
    return {
        "computed_at": row.computed_at.isoformat(),
        "kind": row.kind,
        "data_type": row.data_type,
        "nullable": row.nullable,
        "position": row.position,
        "total_count": row.total_count,
        "null_count": row.null_count,
        "zero_count": row.zero_count,
        "empty_count": row.empty_count,
        "distinct_count": row.distinct_count,
        "p_min": row.p_min, "p_max": row.p_max,
        "p_mean": row.p_mean, "p_stddev": row.p_stddev,
        "p2": row.p2, "p5": row.p5, "p10": row.p10,
        "p25": row.p25, "p50": row.p50, "p75": row.p75,
        "p90": row.p90, "p95": row.p95, "p98": row.p98, "p99": row.p99,
        "histogram": row.histogram or [],
        "top_values": row.top_values or [],
    }


async def _compute_and_cache(
    dataset_id: str, column: str, db: AsyncSession
) -> ColumnStatsCache:
    _, s = await _get_source_for_dataset(dataset_id, db)
    schema = _default_schema_for_source(s)
    # Match check-runner normalisation: if schema is empty and dataset_id encodes "schema.table",
    # extract schema from the dataset_id (e.g. "gigler.gig_prices" → schema="gigler", table="gig_prices")
    if not schema and "." in dataset_id:
        schema, table = dataset_id.rsplit(".", 1)
    else:
        table = dataset_id.split(".")[-1]
    loop = asyncio.get_event_loop()
    adapter = await loop.run_in_executor(None, _make_adapter, s)
    try:
        result = await loop.run_in_executor(None, adapter.profile_column, schema, table, column)
    except Exception as exc:
        log.error("profile_column_failed", dataset_id=dataset_id, column=column, error=str(exc))
        raise HTTPException(status_code=500, detail=f"Profile computation failed: {exc}") from exc

    q = await db.execute(
        select(ColumnStatsCache)
        .where(ColumnStatsCache.dataset_id == dataset_id)
        .where(ColumnStatsCache.column_name == column)
    )
    row = q.scalar_one_or_none()
    if row is None:
        row = ColumnStatsCache(dataset_id=dataset_id, column_name=column)
        db.add(row)

    row.computed_at = datetime.now(timezone.utc)
    row.kind = result.kind
    row.data_type = result.data_type or None
    row.nullable = result.nullable
    row.position = result.position
    row.total_count = result.total_count
    row.null_count = result.null_count
    row.zero_count = result.zero_count
    row.empty_count = result.empty_count
    row.distinct_count = result.distinct_count
    row.p_min = result.p_min
    row.p_max = result.p_max
    row.p_mean = result.p_mean
    row.p_stddev = result.p_stddev
    row.p2 = result.p2
    row.p5 = result.p5
    row.p10 = result.p10
    row.p25 = result.p25
    row.p50 = result.p50
    row.p75 = result.p75
    row.p90 = result.p90
    row.p95 = result.p95
    row.p98 = result.p98
    row.p99 = result.p99
    row.histogram = result.histogram
    row.top_values = result.top_values
    await db.commit()
    await db.refresh(row)

    # Schema history — Option B: record only on change
    last_q = await db.execute(
        select(ColumnSchemaHistory)
        .where(ColumnSchemaHistory.dataset_id == dataset_id)
        .where(ColumnSchemaHistory.column_name == column)
        .order_by(desc(ColumnSchemaHistory.recorded_at))
        .limit(1)
    )
    last = last_q.scalar_one_or_none()
    changed = (
        last is None
        or last.data_type != (result.data_type or None)
        or last.nullable != result.nullable
        or last.position != result.position
    )
    if changed:
        db.add(ColumnSchemaHistory(
            dataset_id=dataset_id,
            column_name=column,
            data_type=result.data_type or None,
            nullable=result.nullable,
            position=result.position,
        ))
        await db.commit()

    return row


@router.get("/datasets/{dataset_id}/columns/{column}/stats")
async def get_column_stats(
    dataset_id: str,
    column: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return cached column stats. Computes from warehouse on first call or if prior computation failed."""
    q = await db.execute(
        select(ColumnStatsCache)
        .where(ColumnStatsCache.dataset_id == dataset_id)
        .where(ColumnStatsCache.column_name == column)
    )
    row = q.scalar_one_or_none()
    if row is not None and row.total_count is not None:
        return _row_to_dict(row)
    row = await _compute_and_cache(dataset_id, column, db)
    return _row_to_dict(row)


@router.post("/datasets/{dataset_id}/columns/{column}/refresh-stats", status_code=200)
async def refresh_column_stats(
    dataset_id: str,
    column: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Force-recompute stats from warehouse and update cache."""
    row = await _compute_and_cache(dataset_id, column, db)
    return _row_to_dict(row)


@router.get("/datasets/{dataset_id}/columns/{column}/schema-history")
async def get_column_schema_history(
    dataset_id: str,
    column: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    q = await db.execute(
        select(ColumnSchemaHistory)
        .where(ColumnSchemaHistory.dataset_id == dataset_id)
        .where(ColumnSchemaHistory.column_name == column)
        .order_by(ColumnSchemaHistory.recorded_at)
    )
    return [
        {
            "id": r.id,
            "data_type": r.data_type,
            "nullable": r.nullable,
            "position": r.position,
            "recorded_at": r.recorded_at.isoformat(),
        }
        for r in q.scalars().all()
    ]


@router.get("/datasets/{dataset_id}/columns/{column}/incidents")
async def get_column_incidents(
    dataset_id: str,
    column: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    q = await db.execute(
        select(Incident)
        .where(Incident.dataset_id == dataset_id)
        .where(Incident.column_name == column)
        .order_by(desc(Incident.opened_at))
        .limit(limit)
    )
    return [
        {
            "id": r.id,
            "detector_slug": r.detector_slug,
            "severity": r.severity,
            "message": r.message,
            "status": r.status,
            "opened_at": r.opened_at.isoformat(),
            "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
        }
        for r in q.scalars().all()
    ]
