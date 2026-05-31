"""REST API routes for sources, datasets, checks, incidents."""
from __future__ import annotations

import asyncio
import json
import os
import time as _t
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


class UpdateSourceBody(BaseModel):
    name: str | None = None
    password: str | None = None


@router.patch("/sources/{source_id}")
async def update_source(
    source_id: str,
    body: UpdateSourceBody,
    db: AsyncSession = Depends(get_db),
) -> dict:
    s = await db.get(Source, source_id)
    if s is None:
        raise HTTPException(404, detail=f"Source '{source_id}' not found")
    if body.name is not None:
        s.name = body.name
    if body.password is not None:
        s.password = body.password
    await db.commit()
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
    default_schema = _default_schema_for_source(s)
    for table_name in (new_tables - current_tables):
        # BigQuery tables arrive as "dataset.table"; extract schema from the name.
        if s.engine == "bigquery" and "." in table_name:
            table_schema, _ = table_name.split(".", 1)
        else:
            table_schema = default_schema
        db.add(Dataset(
            id=table_name,
            source_id=source_id,
            schema_name=table_schema,
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


def _suggest_table_sync(
    source: "Source",
    schema: str,
    table: str,
    api_key: str,
    rules_content: str,
) -> list[dict]:
    """Suggest checks for a single table. Runs in a thread with its own adapter."""
    from dqt.checks.suggest import SuggestedCheck, suggest_checks_for_column

    # BigQuery tables arrive as "dataset.table"; split to get actual schema + table.
    actual_schema = schema
    actual_table = table
    if "." in table:
        actual_schema, actual_table = table.split(".", 1)

    try:
        adapter = _make_adapter(source)
        cols = adapter.describe_columns(actual_schema, actual_table)
    except Exception as exc:
        log.warning("suggest_describe_failed", table=table, error=str(exc))
        return []

    col_names = [c.name for c in cols]
    col_types = [c.data_type for c in cols]

    heuristic: dict[str, list[SuggestedCheck]] = {
        c.name: suggest_checks_for_column(_build_profile(c.name, c.data_type, actual_table), use_llm=False)
        for c in cols
    }

    llm: dict[str, list[dict]] = {}
    if api_key and rules_content:
        try:
            _tllm = _t.time()
            llm = _llm_suggest_batch(actual_table, col_names, col_types, rules_content, api_key)
            log.info("suggest_llm_ok", table=table, columns=len(col_names), llm_s=round(_t.time()-_tllm,2))
        except Exception as exc:
            log.warning("suggest_llm_failed", table=table, error=str(exc))

    results: list[dict] = []
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


def _resolve_suggest_context(source: Source) -> tuple[str, str, str]:
    """Resolve (schema, api_key, rules_content) before per-table parallel work."""
    try:
        adapter = _make_adapter(source)
        schema = _default_schema_for_source(source)
        if not schema:
            try:
                schemas = adapter.list_schemas()
                if schemas:
                    schema = schemas[0]
            except Exception:
                pass
    except Exception as exc:
        log.warning("suggest_adapter_failed", source_id=source.id, error=str(exc))
        schema = ""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        log.warning("suggest_no_anthropic_key", note="falling back to heuristics only")
    rules_content = _load_column_concepts() if api_key else ""
    return schema, api_key, rules_content


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
    schema, api_key, rules_content = await loop.run_in_executor(
        None, _resolve_suggest_context, s
    )

    # Each table runs in its own executor slot — truly parallel via asyncio.gather.
    results_nested = await asyncio.gather(*[
        loop.run_in_executor(None, _suggest_table_sync, s, schema, t, api_key, rules_content)
        for t in body.tables
    ])
    return [item for sublist in results_nested for item in sublist]


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
# Detector category map (mirrors frontend DETECTOR_GROUP)
# ------------------------------------------------------------------

_DETECTOR_CATEGORY: dict[str, str] = {
    "completeness": "completeness", "null_fraction": "completeness", "volume": "completeness",
    "volume_anomaly": "completeness", "row_count_in_range": "completeness",
    "freshness_seconds_behind": "completeness", "schema_change": "completeness",
    "uniqueness": "validity", "validity": "validity", "set_membership": "validity",
    "set_exclusion": "validity", "regex_match": "validity", "value_in_range": "validity",
    "string_length_range": "validity", "date_format": "validity", "string_case": "validity",
    "sql_assertion": "validity", "date_part_missing": "validity", "monotonicity": "validity",
    "referential_integrity_rate": "validity", "referential_integrity": "validity",
    "column_pair": "validity", "composite_uniqueness": "validity",
    "max_in_range": "validity", "min_in_range": "validity", "median_in_range": "validity",
    "stddev_in_range": "validity", "sum_in_range": "validity", "cardinality_in_range": "validity",
    "quantile_in_range": "validity", "numeric_mean_shift": "validity", "numeric_mean": "validity",
    "ks_pvalue": "drift", "ks_drift": "drift", "wasserstein_1": "drift", "psi": "drift",
    "kl_divergence": "drift", "js_divergence": "drift", "chi_square_drift": "drift",
    "cramers_v": "drift", "mmd": "drift", "mutual_information": "drift", "benford_law_fit": "drift",
    "mad_outlier_fraction": "outliers", "double_mad_outlier_fraction": "outliers",
    "zscore_outlier_fraction": "outliers", "adjusted_boxplot_fraction": "outliers",
    "iqr_fence": "outliers", "grubbs": "outliers", "generalized_esd": "outliers",
    "outlier_fraction_drift": "outliers",
    "isolation_forest_fraction": "outliers", "mahalanobis_distance": "outliers",
    "lof": "outliers", "one_class_svm": "outliers", "hbos": "outliers", "ecod": "outliers",
    "stl_residual_zscore": "timeseries", "cusum": "timeseries", "page_hinkley": "timeseries",
    "holt_winters": "timeseries", "prophet_anomaly": "timeseries", "adwin": "timeseries",
    "bocpd": "timeseries", "matrix_profile": "timeseries",
}


# ------------------------------------------------------------------
# Columns — all monitored columns across all datasets
# ------------------------------------------------------------------

@router.get("/columns")
async def list_all_columns(db: AsyncSession = Depends(get_db)) -> list[dict]:
    """Return every monitored column (has at least one ColumnCheck) with check counts and verdict counts."""
    from collections import defaultdict  # noqa: PLC0415

    checks_q = await db.execute(
        select(ColumnCheck.dataset_id, ColumnCheck.column_name, ColumnCheck.detector_slug)
        .where(ColumnCheck.column_name.isnot(None))
        .order_by(ColumnCheck.dataset_id, ColumnCheck.column_name)
    )
    all_checks = checks_q.all()
    if not all_checks:
        return []

    dataset_ids: set[str] = {r.dataset_id for r in all_checks}

    datasets_q = await db.execute(select(Dataset).where(Dataset.id.in_(dataset_ids)))
    datasets: dict[str, Dataset] = {d.id: d for d in datasets_q.scalars()}

    source_ids = {d.source_id for d in datasets.values()}
    sources_q = await db.execute(select(Source).where(Source.id.in_(source_ids)))
    sources: dict[str, Source] = {s.id: s for s in sources_q.scalars()}

    # Latest verdict per (dataset_id, column_name, detector_slug)
    runs_q = await db.execute(
        select(CheckRun.dataset_id, CheckRun.column_name, CheckRun.detector_slug, CheckRun.verdict, CheckRun.ran_at)
        .where(CheckRun.dataset_id.in_(dataset_ids))
        .order_by(desc(CheckRun.ran_at))
        .limit(5000)
    )
    latest_det_verdict: dict[tuple[str, str | None, str], str] = {}
    for row in runs_q.all():
        det_key = (row.dataset_id, row.column_name, row.detector_slug)
        if det_key not in latest_det_verdict:
            latest_det_verdict[det_key] = row.verdict or "unknown"

    verdict_counts_map: dict[tuple[str, str | None], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for (did, cn, _), v in latest_det_verdict.items():
        verdict_counts_map[(did, cn)][v] += 1

    # DQT score per column: verdict-based quality score (pass=100, warn=50, fail=0).
    # Minimum across all latest check runs for the column.
    _VERDICT_SCORE = {"pass": 100, "warn": 50, "fail": 0, "error": 0}
    dqt_score_map: dict[tuple[str, str | None], int] = {}
    for (did, cn, _), v in latest_det_verdict.items():
        vs = _VERDICT_SCORE.get(v)
        if vs is not None:
            key = (did, cn)
            if key not in dqt_score_map or vs < dqt_score_map[key]:
                dqt_score_map[key] = vs

    _RANK = {"fail": 3, "error": 3, "warn": 2, "pass": 1}
    latest_verdict: dict[tuple[str, str | None], str] = {}
    for (did, cn), vc in verdict_counts_map.items():
        worst = "pending"
        for v in ["fail", "error", "warn", "pass"]:
            if vc.get(v, 0) > 0:
                worst = v
                break
        latest_verdict[(did, cn)] = worst

    # Metric indicator: column is a metric if a MetricDefinition exists with matching
    # (dataset, column_name), or if a table-level metric exists (column_name IS NULL).
    metrics_rows = (await db.execute(
        select(MetricDefinition.dataset, MetricDefinition.column_name)
        .where(MetricDefinition.dataset.in_(dataset_ids))
    )).all()
    col_metric_keys: set[tuple[str, str]] = {
        (r.dataset, r.column_name) for r in metrics_rows if r.column_name is not None
    }
    table_metric_datasets: set[str] = {
        r.dataset for r in metrics_rows if r.column_name is None
    }

    # Build per-column category counts
    col_cats: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in all_checks:
        cat = _DETECTOR_CATEGORY.get(r.detector_slug, "custom")
        col_cats[(r.dataset_id, r.column_name)][cat] += 1

    result = []
    for (dataset_id, col_name), cat_counts in sorted(col_cats.items()):
        d = datasets.get(dataset_id)
        s = sources.get(d.source_id) if d else None
        result.append({
            "source_id": d.source_id if d else "",
            "source_name": s.name if s else (d.source_id if d else ""),
            "source_engine": s.engine if s else "",
            "dataset_id": dataset_id,
            "column": col_name,
            "check_counts": dict(cat_counts),
            "verdict_counts": dict(verdict_counts_map.get((dataset_id, col_name), {})),
            "total_checks": sum(cat_counts.values()),
            "is_metric": (
                (dataset_id, col_name) in col_metric_keys or
                dataset_id in table_metric_datasets
            ),
            "worst_verdict": latest_verdict.get((dataset_id, col_name), "pending"),
            "dqt_score": dqt_score_map.get((dataset_id, col_name)),
        })
    return result


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

    # Compute live check_count and last_run_at from actual data (two separate queries to avoid join multiplication)
    check_count_q = await db.execute(
        select(func.count(ColumnCheck.id))
        .where(ColumnCheck.dataset_id == dataset_id, ColumnCheck.enabled.is_(True))
    )
    live_check_count: int = check_count_q.scalar() or 0

    last_run_q = await db.execute(
        select(func.max(CheckRun.ran_at)).where(CheckRun.dataset_id == dataset_id)
    )
    live_last_run_at: datetime | None = last_run_q.scalar()

    runs_q = await db.execute(
        select(CheckRun)
        .where(CheckRun.dataset_id == dataset_id)
        .order_by(desc(CheckRun.ran_at))
        .limit(500)
    )
    runs = runs_q.scalars().all()

    # One result per (column, detector) pair — latest run
    seen: set[tuple[str | None, str]] = set()
    latest_runs: list[CheckRun] = []
    for r in runs:
        key = (r.column_name, r.detector_slug)
        if key not in seen:
            seen.add(key)
            latest_runs.append(r)

    base = _dataset_dict(d)
    base["check_count"] = live_check_count
    base["last_run"] = _time_ago(live_last_run_at)
    return {
        **base,
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
    from sqlalchemy import text as _text
    params: dict = {}
    sql = """
        SELECT cc.id, cc.dataset_id, cc.column_name, cc.detector_slug, cc.params, cc.enabled,
               cr.verdict, cr.score, cr.ran_at, cr.plain_english
        FROM column_checks cc
        LEFT JOIN LATERAL (
            SELECT verdict, score, ran_at, plain_english FROM check_runs
            WHERE dataset_id = cc.dataset_id
              AND column_name = cc.column_name
              AND detector_slug = cc.detector_slug
            ORDER BY ran_at DESC LIMIT 1
        ) cr ON true
    """
    if dataset_id:
        sql += " WHERE cc.dataset_id = :dataset_id"
        params["dataset_id"] = dataset_id
    sql += " ORDER BY cc.created_at DESC LIMIT 1000"

    rows = (await db.execute(_text(sql), params)).fetchall()
    output = []
    for r in rows:
        row_verdict = r.verdict if r.verdict else "pending"
        if verdict is not None and row_verdict != verdict:
            continue
        output.append({
            "id": r.id,
            "dataset_id": r.dataset_id,
            "column": r.column_name,
            "detector": r.detector_slug,
            "params": r.params,
            "enabled": r.enabled if r.enabled is not None else True,
            "verdict": row_verdict,
            "score": r.score,
            "ran_at": r.ran_at.isoformat() if r.ran_at else None,
            "ran_at_ago": _time_ago(r.ran_at) if r.ran_at else None,
            "plain_english": r.plain_english if r.verdict else None,
        })
    return output


@router.get("/checks/{check_id}/sql")
async def get_check_sql(check_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Return the SQL that this specific check runs against the warehouse."""
    from dqt.algorithms._registry import registry
    from dqt.algorithms._base import BaseAggregateDetector
    from dqt_server.models.core import ColumnCheck
    check = await db.get(ColumnCheck, check_id)
    if check is None:
        raise HTTPException(404, detail=f"Check '{check_id}' not found")
    slug = check.detector_slug
    params = check.params or {}
    col = check.column_name
    dataset_id = check.dataset_id
    try:
        detector_cls = registry.get(slug)
    except KeyError:
        raise HTTPException(400, detail=f"Unknown detector: '{slug}'")
    constructor_params = {k: v for k, v in params.items() if k not in {"warn_threshold", "fail_threshold"}}
    try:
        detector = detector_cls(**constructor_params)
    except Exception:
        # Windowed detectors (e.g. ks_drift): generate template SQL from stored params
        if "date_col" in constructor_params:
            from datetime import date as _date, timedelta
            date_col = str(constructor_params.get("date_col") or "").strip() or "<date_column>"
            ref_days = int(constructor_params.get("reference_days", 30))
            curr_days = int(constructor_params.get("current_days", 7))
            today = _date.today()
            curr_start = today - timedelta(days=curr_days - 1)
            ref_end = curr_start - timedelta(days=1)
            ref_start = ref_end - timedelta(days=ref_days - 1)
            sql = (
                f"-- {slug} on {dataset_id}.{col}\n"
                f"-- Reference window (control)\n"
                f"SELECT {col}\nFROM {dataset_id}\nWHERE {date_col} >= '{ref_start}' AND {date_col} <= '{ref_end}';\n\n"
                f"-- Current window (test)\n"
                f"SELECT {col}\nFROM {dataset_id}\nWHERE {date_col} >= '{curr_start}' AND {date_col} <= '{today}';"
            )
            return {"sql": sql, "check_id": check_id}
        raise HTTPException(400, detail=f"Cannot instantiate detector: {constructor_params}")
    if isinstance(detector, BaseAggregateDetector):
        try:
            agg_exprs = detector.get_aggregations(col)
        except Exception as exc:
            raise HTTPException(500, detail=f"Cannot generate SQL: {exc}")
        selects = ",\n       ".join(f"{expr.sql} AS {expr.name}" for expr in agg_exprs)
        sql = f"-- {slug} on {dataset_id}.{col}\nSELECT {selects}\nFROM {dataset_id};"
        return {"sql": sql, "check_id": check_id}

    if hasattr(detector, "get_sample_filters"):
        try:
            ref_where, curr_where = detector.get_sample_filters()
        except Exception as exc:
            raise HTTPException(500, detail=f"Cannot generate SQL: {exc}")
        sql = (
            f"-- {slug} on {dataset_id}.{col}\n"
            f"-- Reference window (control)\n"
            f"SELECT {col}\nFROM {dataset_id}\nWHERE {ref_where};\n\n"
            f"-- Current window (test)\n"
            f"SELECT {col}\nFROM {dataset_id}\nWHERE {curr_where};"
        )
        return {"sql": sql, "check_id": check_id}

    sql = (
        f"-- {slug} on {dataset_id}.{col}\n"
        f"-- Statistical sample (full-table pull; limit as needed)\n"
        f"SELECT {col}\nFROM {dataset_id}\nLIMIT 1000;"
    )
    return {"sql": sql, "check_id": check_id}


@router.get("/checks/sql")
async def get_checks_sql(db: AsyncSession = Depends(get_db)) -> dict:
    """Return SQL for all checks that have run at least once (for pasting into a SQL client)."""
    from dqt.algorithms._registry import registry
    from dqt.algorithms._base import BaseAggregateDetector
    from sqlalchemy import text as _text

    rows = (await db.execute(_text("""
        SELECT cc.dataset_id, cc.column_name, cc.detector_slug, cc.params
        FROM column_checks cc
        WHERE EXISTS (
            SELECT 1 FROM check_runs cr
            WHERE cr.dataset_id = cc.dataset_id
              AND cr.column_name = cc.column_name
              AND cr.detector_slug = cc.detector_slug
        )
        ORDER BY cc.dataset_id, cc.column_name, cc.detector_slug
    """))).fetchall()

    sqls: list[str] = []
    for r in rows:
        slug = r.detector_slug
        params = r.params or {}
        col = r.column_name
        dataset_id = r.dataset_id
        try:
            detector_cls = registry.get(slug)
            constructor_params = {k: v for k, v in params.items()
                                  if k not in {"warn_threshold", "fail_threshold"}}
            detector = detector_cls(**constructor_params)
        except Exception:
            continue
        if not isinstance(detector, BaseAggregateDetector):
            continue
        try:
            agg_exprs = detector.get_aggregations(col)
        except Exception:
            continue
        selects = ",\n       ".join(f"{expr.sql} AS {expr.name}" for expr in agg_exprs)
        sqls.append(f"-- {slug} on {dataset_id}.{col}\nSELECT {selects}\nFROM {dataset_id};")

    return {"sql": "\n\n".join(sqls)}


@router.post("/checks/refresh", status_code=202)
async def refresh_checks() -> dict:
    """Fire-and-forget: start a full check refresh in the background."""
    import asyncio
    asyncio.create_task(check_runner.refresh())
    return {"status": "accepted"}


@router.get("/checks/running")
async def checks_running_status() -> dict:
    """Return whether a full refresh is currently in progress."""
    return {"running": check_runner._refreshing}


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


@router.get("/datasets/{dataset_id}/columns")
async def list_dataset_columns(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return column metadata for a dataset, fetched live from the warehouse."""
    d = await db.get(Dataset, dataset_id)
    if d is None:
        raise HTTPException(404, detail=f"Dataset '{dataset_id}' not found")
    s = await db.get(Source, d.source_id)
    if s is None:
        raise HTTPException(404, detail=f"Source '{d.source_id}' not found")
    loop = asyncio.get_event_loop()

    def _fetch() -> list[dict]:
        adapter = _make_adapter(s)
        # For BQ, dataset_id is "schema.table"; split accordingly
        if s.engine == "bigquery" and "." in dataset_id:
            schema, table = dataset_id.split(".", 1)
        else:
            schema = _default_schema_for_source(s) or d.schema_name or "public"
            table = dataset_id
        try:
            cols = adapter.describe_columns(schema, table)
            return [{"name": c.name, "data_type": c.data_type, "nullable": c.nullable, "position": c.position} for c in cols]
        except Exception as exc:
            log.warning("dataset_columns_failed", dataset=dataset_id, error=str(exc))
            return []

    return await loop.run_in_executor(None, _fetch)


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


@router.get("/datasets/{dataset_id}/columns/{column}/history")
async def get_column_run_history(
    dataset_id: str,
    column: str,
    days: int = 90,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return CheckRun history for a column over the last N days, for time-series charting."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    q = (
        select(CheckRun)
        .where(
            CheckRun.dataset_id == dataset_id,
            CheckRun.column_name == column,
            CheckRun.ran_at >= cutoff,
        )
        .order_by(CheckRun.ran_at)
        .limit(1000)
    )
    result = await db.execute(q)
    return [
        {
            "id": r.id,
            "detector": r.detector_slug,
            "score": r.score,
            "verdict": r.verdict,
            "ran_at": r.ran_at.isoformat(),
        }
        for r in result.scalars().all()
    ]


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
