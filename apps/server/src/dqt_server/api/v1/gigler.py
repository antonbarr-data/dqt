"""REST API routes for sources, datasets, checks, incidents."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone, timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dqt_server.db.engine import get_db
from dqt_server.gigler_service import (
    _make_adapter, _default_schema_for_source, _list_tables_for_source_sync,
    gigler_service,
)
from dqt_server.models.gigler import CheckRun, ColumnCheck, Dataset, Incident, Source

_STEP_DISPLAY = {
    "tcp_reach": "TCP Reach",
    "auth": "Authentication",
    "info_schema": "Info Schema Read",
    "sample_select": "Sample SELECT",
    "latency_probe": "Latency Probe",
    "clock_skew": "Clock Skew",
}


def _run_health_check_sync(
    engine: str, host: str, port: int, username: str, password: str, secure: bool, db_name: str
) -> dict:
    engine_lc = engine.lower()
    if engine_lc == "clickhouse":
        from dqt.adapters.clickhouse.adapter import ClickHouseAdapter
        from dqt.adapters.clickhouse.config import ClickHouseConfig
        cfg = ClickHouseConfig(
            host=host, port=port, database=db_name,
            username=username, password=password, secure=secure,
        )
        adapter = ClickHouseAdapter(**cfg.to_client_kwargs())
        hc = adapter.health_check()
    elif engine_lc == "postgres":
        from dqt.adapters.postgres.adapter import PostgresAdapter
        conn_str = f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{db_name}"
        adapter = PostgresAdapter(conn_str)
        hc = adapter.health_check()
    else:
        raise ValueError(f"Health check for engine '{engine}' is not yet supported")
    return {
        "steps": [
            {
                "name": s.name,
                "display": _STEP_DISPLAY.get(s.name, s.name),
                "status": s.status,
                "latency_ms": round(s.latency_ms, 1),
                "detail": s.detail,
            }
            for s in hc.steps
        ],
        "passed": hc.passed,
    }


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
        "secure": getattr(s, "secure", False),
        "username": s.username or "",
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

class SourceTestBody(BaseModel):
    engine: str
    host: str
    port: int
    username: str = ""
    password: str = ""
    secure: bool = False
    db_name: str = "default"


class SourceCreateBody(BaseModel):
    name: str
    engine: str
    host: str
    port: int
    username: str = ""
    password: str = ""
    secure: bool = False
    db_name: str = "default"


@router.post("/sources/test")
async def test_source_connection(body: SourceTestBody) -> dict:
    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(
            None,
            _run_health_check_sync,
            body.engine, body.host, body.port,
            body.username, body.password, body.secure, body.db_name,
        )
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc))


@router.post("/sources", status_code=201)
async def create_source(body: SourceCreateBody, db: AsyncSession = Depends(get_db)) -> dict:
    source_id = f"{body.engine.lower()}-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)
    source = Source(
        id=source_id,
        name=body.name,
        engine=body.engine,
        host=body.host,
        port=body.port,
        db_name=body.db_name,
        username=body.username,
        password=body.password,
        secure=body.secure,
        status="unknown",
        table_count=0,
        created_at=now,
    )
    db.add(source)
    await db.commit()
    return _source_dict(source)


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


class UpdateTablesBody(BaseModel):
    tables: list[str]


@router.get("/sources/{source_id}/tables")
async def list_source_tables(source_id: str, db: AsyncSession = Depends(get_db)) -> list[dict]:
    s = await db.get(Source, source_id)
    if s is None:
        raise HTTPException(404, detail=f"Source '{source_id}' not found")

    result = await db.execute(select(Dataset).where(Dataset.source_id == source_id))
    watched = {d.id for d in result.scalars().all()}

    loop = asyncio.get_event_loop()
    try:
        all_tables = await loop.run_in_executor(None, _list_tables_for_source_sync, s)
    except Exception:
        all_tables = [{"schema": _default_schema_for_source(s), "name": t} for t in sorted(watched)]

    if not all_tables:
        all_tables = [{"schema": _default_schema_for_source(s), "name": t} for t in sorted(watched)]

    return [
        {"name": t["name"], "schema": t["schema"], "watched": t["name"] in watched}
        for t in all_tables
    ]


@router.put("/sources/{source_id}/tables")
async def update_source_tables(
    source_id: str,
    body: UpdateTablesBody,
    db: AsyncSession = Depends(get_db),
) -> dict:
    s = await db.get(Source, source_id)
    if s is None:
        raise HTTPException(404, detail=f"Source '{source_id}' not found")

    new_tables = set(body.tables)
    result = await db.execute(select(Dataset).where(Dataset.source_id == source_id))
    current_datasets = {d.id: d for d in result.scalars().all()}
    current_tables = set(current_datasets.keys())

    for table_id in (current_tables - new_tables):
        await db.delete(current_datasets[table_id])

    now = datetime.now(timezone.utc)
    schema = _default_schema_for_source(s)
    for table_name in (new_tables - current_tables):
        db.add(Dataset(
            id=table_name,
            source_id=source_id,
            schema_name=schema,
            status="unknown",
            check_count=0,
            created_at=now,
        ))

    s.table_count = len(new_tables)
    await db.commit()

    if new_tables - current_tables:
        asyncio.create_task(gigler_service.refresh())

    return {"source_id": source_id, "tables": sorted(new_tables)}


# ------------------------------------------------------------------
# Suggest checks for a source (used by wizard step 4)
# ------------------------------------------------------------------

class SuggestChecksBody(BaseModel):
    tables: list[str]


def _suggest_checks_sync(source: Source, tables: list[str]) -> list[dict]:
    """Get AI-powered check suggestions for selected tables in a source."""
    from dqt.checks.suggest import ColumnProfile, suggest_checks_for_column

    results: list[dict] = []
    try:
        adapter = _make_adapter(source)
        schema = _default_schema_for_source(source)
    except Exception as exc:
        log.warning("suggest_adapter_failed", source_id=source.id, error=str(exc))
        return results

    for table in tables:
        try:
            cols = adapter.describe_columns(schema, table)
        except Exception as exc:
            log.warning("suggest_describe_failed", table=table, error=str(exc))
            continue

        for col in cols:
            name_lower = col.name.lower()
            profile = ColumnProfile(
                name=col.name,
                data_type=col.data_type,
                null_fraction=0.0,
                distinct_count=0,
                sample_values=[],
                min_value=None,
                max_value=None,
                is_likely_pk=name_lower in ("id", f"{table}_id", "pk"),
                is_likely_fk=(
                    name_lower.endswith("_id")
                    and name_lower not in ("id",)
                    and name_lower != f"{table}_id"
                ),
                is_likely_enum=False,
                is_likely_email="email" in name_lower,
                is_likely_timestamp=any(
                    t in col.data_type.lower()
                    for t in ("timestamp", "datetime", "date")
                ) or any(k in name_lower for k in ("_at", "_date", "timestamp", "created", "updated")),
                is_likely_currency=any(
                    k in name_lower
                    for k in ("amount", "price", "revenue", "cost", "fee", "total", "usd", "eur")
                ),
                is_likely_country=name_lower in ("country", "country_code", "country_iso"),
                sample_size_used=0,
            )
            suggestions = suggest_checks_for_column(profile, use_llm=True)
            for sugg in suggestions:
                tier = (
                    "essential" if sugg.confidence >= 0.80
                    else "recommended" if sugg.confidence >= 0.60
                    else "full_coverage"
                )
                results.append({
                    "table": table,
                    "column": col.name,
                    "detector_slug": sugg.detector_slug,
                    "params": sugg.params,
                    "rationale": sugg.rationale,
                    "confidence": round(sugg.confidence, 3),
                    "tier": tier,
                })

    return results


@router.post("/sources/{source_id}/suggest-checks")
async def suggest_checks_for_source(
    source_id: str,
    body: SuggestChecksBody,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    s = await db.get(Source, source_id)
    if s is None:
        raise HTTPException(404, detail=f"Source '{source_id}' not found")
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _suggest_checks_sync, s, body.tables)


# ------------------------------------------------------------------
# Column checks (user-defined)
# ------------------------------------------------------------------

class ColumnCheckBatchItem(BaseModel):
    dataset_id: str
    column_name: str
    detector_slug: str
    params: dict = {}
    rationale: str = ""


class ColumnCheckBatchBody(BaseModel):
    checks: list[ColumnCheckBatchItem]


@router.post("/column-checks/batch", status_code=201)
async def create_column_checks_batch(
    body: ColumnCheckBatchBody,
    db: AsyncSession = Depends(get_db),
) -> dict:
    now = datetime.now(timezone.utc)
    created = 0
    for item in body.checks:
        check_id = f"{item.dataset_id}.{item.column_name}.{item.detector_slug}"
        existing = await db.get(ColumnCheck, check_id)
        if existing is None:
            db.add(ColumnCheck(
                id=check_id,
                dataset_id=item.dataset_id,
                column_name=item.column_name,
                detector_slug=item.detector_slug,
                params=item.params,
                rationale=item.rationale,
                created_at=now,
                updated_at=now,
            ))
            created += 1
    await db.commit()
    return {"created": created}


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

    runs_q = await db.execute(
        select(CheckRun)
        .where(CheckRun.dataset_id == dataset_id)
        .order_by(desc(CheckRun.ran_at))
        .limit(200)
    )
    runs = runs_q.scalars().all()

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
    """Trigger a non-blocking refresh of all warehouse checks."""
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
    s = await db.get(Source, d.source_id)
    if s is None:
        raise HTTPException(404, detail=f"Source '{d.source_id}' not found")
    schema = _default_schema_for_source(s)
    loop = asyncio.get_event_loop()
    adapter = await loop.run_in_executor(None, _make_adapter, s)
    return await loop.run_in_executor(
        None, gigler_service._profile_column_sync, adapter, schema, dataset_id, column
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

    if not activity_items:
        activity_items = [
            {"time": "just now", "text": "No incidents recorded yet", "kind": "info"}
        ]

    return {
        "kpis": {
            "open_incidents": open_count,
            "datasets_watched": dataset_count,
            "checks_running": check_count,
            "auto_explained": 0,
        },
        "datasets": [{"id": d.id, "status": d.status} for d in datasets],
        "activity": activity_items,
    }
