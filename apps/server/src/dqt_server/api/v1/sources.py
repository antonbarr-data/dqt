"""REST API routes for sources, datasets, checks, incidents."""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import delete as sa_delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dqt_server.db.engine import get_db
from dqt_server.check_runner import (
    _make_adapter, _default_schema_for_source, _list_tables_for_source_sync,
    check_runner,
)
from dqt_server.models.core import CheckRun, ColumnCheck, Dataset, Incident, MetricDefinition, Source

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
    elif engine_lc == "bigquery":
        from dqt.adapters.bigquery.adapter import BigQueryAdapter
        from dqt_server.check_runner import _bq_credentials_from_password
        creds, inferred_project = _bq_credentials_from_password(password or "")
        project = host or inferred_project or ""
        adapter = BigQueryAdapter(project=project, credentials=creds)
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
router = APIRouter(prefix="/api/v1", tags=["sources"])


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


@router.delete("/sources/{source_id}", status_code=204)
async def delete_source(source_id: str, db: AsyncSession = Depends(get_db)) -> None:
    s = await db.get(Source, source_id)
    if s is None:
        raise HTTPException(404, detail=f"Source '{source_id}' not found")

    datasets_q = await db.execute(select(Dataset).where(Dataset.source_id == source_id))
    datasets = list(datasets_q.scalars().all())
    dataset_ids = [d.id for d in datasets]

    if dataset_ids:
        # ColumnChecks and MetricDefinitions have no ORM cascade — delete manually first.
        await db.execute(sa_delete(ColumnCheck).where(ColumnCheck.dataset_id.in_(dataset_ids)))
        await db.execute(
            sa_delete(MetricDefinition).where(MetricDefinition.dataset.in_(dataset_ids))
        )
        # ORM delete triggers cascade for CheckRuns + Incidents.
        for d in datasets:
            await db.delete(d)

    await db.delete(s)
    await db.commit()
    return Response(status_code=204)


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
        asyncio.create_task(check_runner.refresh())

    return {"source_id": source_id, "tables": sorted(new_tables)}


# ------------------------------------------------------------------
# Suggest checks for a source (used by wizard step 4)
# ------------------------------------------------------------------

class SuggestChecksBody(BaseModel):
    tables: list[str]


_COLUMN_CONCEPTS_PATH = Path(__file__).parent.parent.parent / "data" / "column_concepts.md"


def _load_column_concepts() -> str:
    try:
        return _COLUMN_CONCEPTS_PATH.read_text(encoding="utf-8")
    except OSError:
        log.warning("column_concepts_missing", path=str(_COLUMN_CONCEPTS_PATH))
        return ""


def _llm_suggest_batch(
    table: str,
    col_names: list[str],
    col_types: list[str],
    rules_content: str,
    api_key: str,
) -> dict[str, list[dict]]:
    """One Claude call for all columns in a table. Returns {col_name: [check_dict]}."""
    import anthropic

    col_lines = "\n".join(
        f"- {name} (SQL type: {dtype})"
        for name, dtype in zip(col_names, col_types)
    )

    prompt = (
        f"You are a data quality expert. Using the reference guide below, "
        f"suggest data quality checks for each column in the table `{table}`.\n\n"
        f"## Reference: dqt Column Concepts and Recommended Checks\n\n"
        f"{rules_content}\n\n"
        f"## Columns to analyse\n\n"
        f"{col_lines}\n\n"
        f"For each column, identify its closest concept from the reference guide "
        f"and return the most appropriate checks.\n"
        f"Rules:\n"
        f"- Use detector_slug values exactly as listed in the reference guide\n"
        f"- Only include checks with confidence > 0.6\n"
        f"- Do not repeat checks already obvious from the type alone\n"
        f"- Reply ONLY with valid JSON, no markdown fences:\n"
        f'{{"column_name": [{{"detector_slug": "...", "params": {{}}, "rationale": "...", "confidence": 0.85}}]}}'
    )

    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    # Strip markdown code fences if model adds them
    if raw.startswith("```"):
        raw = "\n".join(
            line for line in raw.splitlines()
            if not line.startswith("```")
        ).strip()

    parsed = json.loads(raw)
    result: dict[str, list[dict]] = {}
    for col_name, checks in parsed.items():
        if isinstance(checks, list):
            result[col_name] = [
                c for c in checks
                if isinstance(c, dict) and "detector_slug" in c
            ]
    return result


def _build_profile(col_name: str, col_type: str, table: str):
    from dqt.checks.suggest import ColumnProfile
    name_lower = col_name.lower()
    return ColumnProfile(
        name=col_name,
        data_type=col_type,
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
        is_likely_timestamp=(
            any(t in col_type.lower() for t in ("timestamp", "datetime", "date"))
            or any(k in name_lower for k in ("_at", "_date", "timestamp", "created", "updated"))
        ),
        is_likely_currency=any(
            k in name_lower for k in ("amount", "price", "revenue", "cost", "fee", "total", "usd", "eur")
        ),
        is_likely_country=name_lower in ("country", "country_code", "country_iso"),
        sample_size_used=0,
    )


def _suggest_checks_sync(source: Source, tables: list[str]) -> list[dict]:
    """Suggest data quality checks for selected tables using heuristics + Claude AI."""
    from dqt.checks.suggest import SuggestedCheck, suggest_checks_for_column

    results: list[dict] = []
    try:
        adapter = _make_adapter(source)
        schema = _default_schema_for_source(source)
        # If schema is empty (e.g. BigQuery with no dataset configured), pick the first available.
        if not schema:
            try:
                schemas = adapter.list_schemas()
                if schemas:
                    schema = schemas[0]
            except Exception:
                pass
    except Exception as exc:
        log.warning("suggest_adapter_failed", source_id=source.id, error=str(exc))
        return results

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        log.warning("suggest_no_anthropic_key", note="falling back to heuristics only")
    rules_content = _load_column_concepts() if api_key else ""

    for table in tables:
        try:
            cols = adapter.describe_columns(schema, table)
        except Exception as exc:
            log.warning("suggest_describe_failed", table=table, error=str(exc))
            continue

        col_names = [c.name for c in cols]
        col_types = [c.data_type for c in cols]

        # Heuristic suggestions (always run, no API needed)
        heuristic: dict[str, list[SuggestedCheck]] = {
            c.name: suggest_checks_for_column(_build_profile(c.name, c.data_type, table), use_llm=False)
            for c in cols
        }

        # LLM suggestions: one call for the whole table
        llm: dict[str, list[dict]] = {}
        if api_key and rules_content:
            try:
                llm = _llm_suggest_batch(table, col_names, col_types, rules_content, api_key)
                log.info("suggest_llm_ok", table=table, columns=len(col_names))
            except Exception as exc:
                log.warning("suggest_llm_failed", table=table, error=str(exc))

        # Merge: heuristic baseline + LLM additions, dedup by slug (highest confidence wins)
        for col in cols:
            all_suggestions: list[SuggestedCheck] = list(heuristic[col.name])
            for llm_check in llm.get(col.name, []):
                all_suggestions.append(SuggestedCheck(
                    detector_slug=llm_check["detector_slug"],
                    params=llm_check.get("params", {}),
                    rationale=llm_check.get("rationale", ""),
                    confidence=float(llm_check.get("confidence", 0.65)),
                ))

            seen: dict[str, SuggestedCheck] = {}
            for s in sorted(all_suggestions, key=lambda x: x.confidence, reverse=True):
                if s.detector_slug not in seen:
                    seen[s.detector_slug] = s

            for sugg in seen.values():
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


@router.delete("/datasets/{dataset_id}", status_code=204)
async def delete_dataset(dataset_id: str, db: AsyncSession = Depends(get_db)) -> None:
    d = await db.get(Dataset, dataset_id)
    if d is None:
        raise HTTPException(404, detail=f"Dataset '{dataset_id}' not found")
    await db.execute(sa_delete(ColumnCheck).where(ColumnCheck.dataset_id == dataset_id))
    await db.execute(
        sa_delete(MetricDefinition).where(MetricDefinition.dataset == dataset_id)
    )
    await db.delete(d)
    await db.commit()
    return Response(status_code=204)


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
    asyncio.create_task(check_runner.refresh())
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
        None, check_runner._profile_column_sync, adapter, schema, dataset_id, column
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

@router.get("/sources/{source_id}/export")
async def export_source_bundle(source_id: str, db: AsyncSession = Depends(get_db)):
    """Export a source + its datasets, checks, and metrics as a YAML bundle."""
    import yaml
    from fastapi.responses import Response

    s = await db.get(Source, source_id)
    if s is None:
        raise HTTPException(404, detail=f"Source '{source_id}' not found")

    datasets_q = await db.execute(select(Dataset).where(Dataset.source_id == source_id))
    datasets = list(datasets_q.scalars().all())

    dataset_ids = [d.id for d in datasets]
    checks_q = await db.execute(
        select(ColumnCheck).where(ColumnCheck.dataset_id.in_(dataset_ids))
    ) if dataset_ids else None
    checks = list(checks_q.scalars().all()) if checks_q else []

    metrics_q = await db.execute(
        select(MetricDefinition).where(MetricDefinition.dataset.in_(dataset_ids))
    ) if dataset_ids else None
    metrics = list(metrics_q.scalars().all()) if metrics_q else []

    bundle = {
        "apiVersion": "dqt/v1",
        "kind": "Bundle",
        "source": {
            "id": s.id,
            "name": s.name,
            "engine": s.engine,
            "host": s.host,
            "port": s.port,
            "db_name": s.db_name,
            "username": s.username or "",
            "secure": getattr(s, "secure", False),
        },
        "datasets": [
            {"id": d.id, "schema": d.schema_name}
            for d in datasets
        ],
        "checks": [
            {
                "dataset_id": c.dataset_id,
                "column": c.column_name,
                "detector": c.detector_slug,
                "params": c.params or {},
                "rationale": c.rationale or "",
            }
            for c in checks
        ],
        "metrics": [
            {
                "fqn": m.fqn,
                "display_name": m.display_name,
                "kind": m.kind,
                "dataset": m.dataset,
                "description": m.description,
                "owners": m.owners or [],
                "tags": m.tags or [],
            }
            for m in metrics
        ],
    }

    content = yaml.dump(bundle, default_flow_style=False, allow_unicode=True, sort_keys=False)
    filename = f"dqt-bundle-{source_id}.yaml"
    return Response(
        content=content,
        media_type="application/x-yaml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
