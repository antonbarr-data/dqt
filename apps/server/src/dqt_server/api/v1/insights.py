"""Insights router -- metric list, detail, series, pin, and explain endpoints."""
from __future__ import annotations

import asyncio
import json as _json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dqt_server.db.engine import get_db
from dqt_server.models.core import MetricCausalEdge, MetricDefinition, MetricRun

from dqt.metrics import Metric, MetricKind, MetricRegistry

router = APIRouter(prefix="/api/v1", tags=["insights"])

_pinned: set[str] = set()
_registry: MetricRegistry | None = None


async def _run_causality_in_background() -> None:
    """Async background task: runs PCMCI+ and persists edges to metric_causal_edges."""
    try:
        from dqt_server.api.v1.causal_compute import _run_discovery_async
        from dqt_server.api.v1.causal_review import _store as _review_store
        await _run_discovery_async(_review_store)
    except Exception:
        pass  # Never crash a metric mutation because causality failed

# Narrative cache keyed by (fqn, lookback_days); TTL 6h
_CACHE_TTL_SECS = 6 * 3600


@dataclass
class _CacheEntry:
    payload: dict
    expires_at: datetime


_narrative_cache: dict[str, _CacheEntry] = {}


def _cache_key(fqn: str, lookback_days: int) -> str:
    return f"{fqn}:{lookback_days}"


def _cache_get(fqn: str, lookback_days: int) -> dict | None:
    key = _cache_key(fqn, lookback_days)
    entry = _narrative_cache.get(key)
    if entry and datetime.now(timezone.utc) < entry.expires_at:
        return entry.payload
    return None


def _cache_set(fqn: str, lookback_days: int, payload: dict) -> None:
    key = _cache_key(fqn, lookback_days)
    _narrative_cache[key] = _CacheEntry(
        payload=payload,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=_CACHE_TTL_SECS),
    )


def _cache_invalidate(fqn: str) -> None:
    for k in [k for k in _narrative_cache if k.startswith(f"{fqn}:")]:
        _narrative_cache.pop(k, None)


async def _load_registry_from_db(db: AsyncSession) -> MetricRegistry:
    global _registry
    result = await db.execute(select(MetricDefinition))
    rows = list(result.scalars().all())

    metrics = [
        Metric(
            fqn=r.fqn,
            display_name=r.display_name,
            kind=r.kind,
            dataset=r.dataset,
            description=r.description,
            owners=r.owners or [],
            tags=r.tags or [],
            warn_threshold=r.warn_threshold,
            fail_threshold=r.fail_threshold,
        )
        for r in rows
    ]
    reg = MetricRegistry(metrics)
    _registry = reg
    return reg


def _get_registry() -> MetricRegistry:
    global _registry
    if _registry is None:
        _registry = MetricRegistry([])
    return _registry


def _metric_to_dict(m: Metric) -> dict:
    return {
        "fqn": m.fqn,
        "display_name": m.display_name,
        "kind": m.kind,
        "dataset": m.dataset,
        "description": m.description,
        "owners": m.owners,
        "tags": m.tags,
        "unit": m.unit,
        "warn_threshold": m.warn_threshold,
        "fail_threshold": m.fail_threshold,
        "current_value": m.current_value,
        "current_verdict": m.current_verdict,
        "last_run": m.last_run,
        "pinned": m.fqn in _pinned,
    }


@router.get("/metrics")
async def list_metrics(db: AsyncSession = Depends(get_db)) -> list[dict]:
    reg = await _load_registry_from_db(db)
    return [_metric_to_dict(m) for m in reg.list()]


class MetricCreate(PydanticBaseModel):
    display_name: str
    kind: str = "ratio"
    dataset: str
    description: str = ""
    owners: list[str] = []
    tags: list[str] = []
    source_id: str | None = None
    expr_type: str | None = None
    expr_sql: str | None = None
    numerator_sql: str | None = None
    denominator_sql: str | None = None
    filter_sql: str | None = None
    time_column: str | None = None


@router.post("/metrics", status_code=201)
async def create_metric(body: MetricCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)) -> dict:
    import re
    slug = re.sub(r"[^a-z0-9_]", "_", body.display_name.lower())
    fqn = f"custom.default.{body.dataset}.{slug}"
    existing = await db.get(MetricDefinition, fqn)
    if existing:
        raise HTTPException(409, detail=f"Metric '{fqn}' already exists")
    m = MetricDefinition(
        fqn=fqn,
        display_name=body.display_name,
        kind=body.kind,
        dataset=body.dataset,
        description=body.description,
        owners=body.owners,
        tags=body.tags,
        source_id=body.source_id,
        expr_type=body.expr_type,
        expr_sql=body.expr_sql,
        numerator_sql=body.numerator_sql,
        denominator_sql=body.denominator_sql,
        filter_sql=body.filter_sql,
        time_column=body.time_column,
        created_at=datetime.now(timezone.utc),
    )
    db.add(m)
    await db.commit()
    global _registry
    _registry = None
    background_tasks.add_task(_run_causality_in_background)
    return {"fqn": fqn, "display_name": body.display_name}


class MetricBatchItem(PydanticBaseModel):
    display_name: str
    kind: str = "ratio"
    dataset: str
    description: str = ""
    owners: list[str] = []
    tags: list[str] = []
    source_id: str | None = None
    column_name: str | None = None
    grain: str | None = None
    additivity: str | None = None
    good_direction: str | None = None
    refresh_cadence: str | None = None
    expr_type: str | None = None
    expr_sql: str | None = None
    numerator_sql: str | None = None
    denominator_sql: str | None = None
    filter_sql: str | None = None
    time_column: str | None = None


class MetricBatchBody(PydanticBaseModel):
    metrics: list[MetricBatchItem]


@router.post("/metrics/batch", status_code=201)
async def create_metrics_batch(body: MetricBatchBody, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)) -> dict:
    import re
    created = 0
    for item in body.metrics:
        slug = re.sub(r"[^a-z0-9_]", "_", item.display_name.lower())
        fqn = f"custom.default.{item.dataset}.{slug}"
        existing = await db.get(MetricDefinition, fqn)
        if existing is None:
            db.add(MetricDefinition(
                fqn=fqn,
                display_name=item.display_name,
                kind=item.kind,
                dataset=item.dataset,
                description=item.description,
                owners=item.owners,
                tags=item.tags,
                source_id=item.source_id,
                column_name=item.column_name,
                grain=item.grain,
                additivity=item.additivity,
                good_direction=item.good_direction,
                refresh_cadence=item.refresh_cadence,
                expr_type=item.expr_type,
                expr_sql=item.expr_sql,
                numerator_sql=item.numerator_sql,
                denominator_sql=item.denominator_sql,
                filter_sql=item.filter_sql,
                time_column=item.time_column,
                created_at=datetime.now(timezone.utc),
            ))
            created += 1
    await db.commit()
    global _registry
    _registry = None
    if created > 0:
        background_tasks.add_task(_run_causality_in_background)
    return {"created": created}


def _infer_kind(col_name: str) -> str:
    n = col_name.lower().split(".")[-1]  # use just the column part if fqn passed
    if any(n.startswith(p) for p in ("n_", "count_", "num_")) or any(n.endswith(s) for s in ("_count", "_n", "_number")):
        return "count"
    if any(n.startswith(p) for p in ("sum_", "total_")) or any(n.endswith(s) for s in ("_sum", "_total")):
        return "sum"
    return "ratio"


class MetricPatch(PydanticBaseModel):
    kind: str | None = None
    description: str | None = None
    owners: list[str] | None = None
    tags: list[str] | None = None
    warn_threshold: float | None = None
    fail_threshold: float | None = None
    grain: str | None = None
    additivity: str | None = None
    good_direction: str | None = None
    refresh_cadence: str | None = None
    lineage: list | None = None
    expr_type: str | None = None
    expr_sql: str | None = None
    numerator_sql: str | None = None
    denominator_sql: str | None = None
    filter_sql: str | None = None
    time_column: str | None = None


@router.patch("/metrics/{fqn:path}", status_code=200)
async def patch_metric(fqn: str, body: MetricPatch, db: AsyncSession = Depends(get_db)) -> dict:
    m = await db.get(MetricDefinition, fqn)
    if m is None:
        raise HTTPException(404, detail=f"Metric '{fqn}' not found")
    if body.kind is not None:
        m.kind = body.kind
    if body.description is not None:
        m.description = body.description
    if body.owners is not None:
        m.owners = body.owners
    if body.tags is not None:
        m.tags = body.tags
    if body.warn_threshold is not None:
        m.warn_threshold = body.warn_threshold
    if body.fail_threshold is not None:
        m.fail_threshold = body.fail_threshold
    if body.grain is not None:
        m.grain = body.grain or None
    if body.additivity is not None:
        m.additivity = body.additivity or None
    if body.good_direction is not None:
        m.good_direction = body.good_direction or None
    if body.refresh_cadence is not None:
        m.refresh_cadence = body.refresh_cadence or None
    if body.lineage is not None:
        m.lineage = body.lineage
    if body.expr_type is not None:
        m.expr_type = body.expr_type or None
    if body.expr_sql is not None:
        m.expr_sql = body.expr_sql or None
    if body.numerator_sql is not None:
        m.numerator_sql = body.numerator_sql or None
    if body.denominator_sql is not None:
        m.denominator_sql = body.denominator_sql or None
    if body.filter_sql is not None:
        m.filter_sql = body.filter_sql or None
    if body.time_column is not None:
        m.time_column = body.time_column or None
    await db.commit()
    global _registry
    _registry = None
    return {"fqn": fqn, "kind": m.kind}


@router.post("/metrics/reinfer-kinds", status_code=200)
async def reinfer_metric_kinds(db: AsyncSession = Depends(get_db)) -> dict:

    result = await db.execute(select(MetricDefinition))
    rows = list(result.scalars().all())
    updated = 0
    for m in rows:
        inferred = _infer_kind(m.display_name or m.fqn)
        if m.kind != inferred:
            m.kind = inferred
            updated += 1
    if updated:
        await db.commit()
        global _registry
        _registry = None
    return {"updated": updated, "total": len(rows)}


# ---------------------------------------------------------------------------
# Metric suggestion pipeline (Stage 1 heuristic + Stage 2 LLM)
# ---------------------------------------------------------------------------

def _heuristic_classify(table: str, column: str, null_rate: float = 0.0) -> str:
    """Classify a column into exactly one bucket. First match wins."""
    t, n = table.lower(), column.lower()
    if (any(t.startswith(p) for p in ("raw_", "staging_", "tmp_")) or
            t.endswith("_archive") or null_rate > 0.5):
        return "reject"
    if any(n.endswith(s) for s in ("_id", "_key", "_uuid", "_sk", "_code")):
        return "key"
    if any(n.endswith(s) for s in ("_at", "_ts", "_date", "_time")):
        return "timestamp"
    if re.search(r"(^created_at$|^updated_at$|^loaded_at$|_by$|^etl_)", n):
        return "audit"
    if any(n.startswith(p) for p in ("is_", "has_", "flag_")):
        return "boolean_flag"
    if (any(t.startswith(p) for p in ("fact_", "agg_", "mart_", "fct_")) or
            any(n.endswith(s) for s in (
                "_amount", "_amt", "_revenue", "_cost", "_price",
                "_qty", "_quantity", "_count", "_duration", "_score",
                "_rate", "_value", "_total", "_balance", "_gmv", "_arr", "_mrr",
            ))):
        return "measure_candidate"
    return "dimension"


def _infer_additivity(column: str) -> str:
    n = column.lower()
    if any(n.endswith(s) for s in ("_balance", "_inventory", "_stock", "_outstanding")):
        return "semi"
    if any(n.endswith(s) for s in ("_rate", "_score", "_ratio", "_pct", "_percent", "_fraction")):
        return "non"
    return "full"


def _infer_grain(table: str) -> str:
    t = table.lower()
    for prefix in ("fact_", "fct_", "agg_", "mart_"):
        if t.startswith(prefix):
            return t[len(prefix):].rstrip("s")
    return "record"


def _llm_suggest_metrics_sync(
    candidates: list[dict],
    dimensions: list[dict],
    timestamps: list[dict],
    api_key: str,
) -> dict:
    """Stage 2: Claude call to propose business metrics. Returns the parsed JSON dict."""
    import anthropic

    system = (
        "You are a senior analytics engineer. From the warehouse columns below, propose at most 7 tracked "
        "business metrics. Rules:\n"
        "- Each metric must map to a recurring decision, have a clear good direction, and be reproducible "
        "from the listed columns alone.\n"
        "- For ratios, specify numerator AND denominator columns separately. Never average an average.\n"
        "- Pair high-leverage metrics with one guardrail where possible.\n"
        "- Mark additivity: full / semi / non.\n"
        "- Drop vanity candidates that drive no decision.\n"
        "- Return STRICT JSON only, no prose."
    )
    user = (
        f"Measure candidates: {_json.dumps(candidates)}\n"
        f"Dimensions: {_json.dumps(dimensions)}\n"
        f"Time columns: {_json.dumps(timestamps)}\n\n"
        'Return:\n{"metrics": [{"name": "...", "definition": "one-line plain English", '
        '"sql_expression": "...", "numerator_columns": ["dataset.col"], '
        '"denominator_columns": ["dataset.col"], "grain": "order|customer|session|...", '
        '"aggregation": "sum|count_distinct|ratio|...", "additivity": "full|semi|non", '
        '"good_direction": "up|down|in_band", "suggested_owner_role": "...", '
        '"guardrail_for": "metric_name or null", "cadence": "daily|weekly|monthly", '
        '"confidence": 0.0, "reasoning": "one sentence"}], '
        '"rejected_candidates": [{"column": "...", "reason": "..."}]}'
    )

    client = anthropic.Anthropic(api_key=api_key)
    for attempt in range(2):
        try:
            msg = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                temperature=0.2,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            raw = msg.content[0].text.strip()
            if raw.startswith("```"):
                raw = "\n".join(ln for ln in raw.splitlines() if not ln.startswith("```")).strip()
            return _json.loads(raw)
        except Exception:
            if attempt == 1:
                raise
    return {"metrics": [], "rejected_candidates": []}


class MetricSuggestItem(PydanticBaseModel):
    dataset: str
    column: str
    null_rate: float = 0.0
    data_type: str = ""
    description: str = ""


class MetricSuggestBody(PydanticBaseModel):
    columns: list[MetricSuggestItem]


@router.post("/metrics/suggest")
async def suggest_metrics(body: MetricSuggestBody) -> dict:
    """Stage 1 heuristic classification + optional Stage 2 LLM enrichment."""
    candidates: list[dict] = []
    dimensions: list[dict] = []
    timestamps: list[dict] = []
    rejected: list[dict] = []

    for col in body.columns:
        bucket = _heuristic_classify(col.dataset, col.column, col.null_rate)
        fqn = f"{col.dataset}.{col.column}"
        entry: dict = {"fqn": fqn, "dataset": col.dataset, "column": col.column,
                       "data_type": col.data_type, "description": col.description}
        if bucket == "measure_candidate":
            entry["additivity"] = _infer_additivity(col.column)
            entry["grain_hint"] = _infer_grain(col.dataset)
            candidates.append(entry)
        elif bucket == "dimension":
            dimensions.append(entry)
        elif bucket == "timestamp":
            timestamps.append(entry)
        else:
            rejected.append({"column": fqn, "reason": bucket.replace("_", " ")})

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    # No heuristic hits — let LLM judge over all non-rejected columns
    if not candidates and api_key and dimensions:
        for d in dimensions:
            d["additivity"] = _infer_additivity(d["column"])
            d["grain_hint"] = _infer_grain(d["dataset"])
        candidates = list(dimensions)
        dimensions = []

    if not candidates:
        return {"metrics": [], "rejected_candidates": rejected}

    if api_key:
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None, lambda: _llm_suggest_metrics_sync(candidates, dimensions, timestamps, api_key)
            )
            for m in result.get("metrics", []):
                nc = (m.get("numerator_columns") or [""])[0]
                parts = nc.split(".")
                m["source_column"] = ".".join(parts[-2:]) if len(parts) >= 2 else nc
                m["dataset"] = parts[-2] if len(parts) >= 2 else (candidates[0]["dataset"] if candidates else "")
                m["display_name"] = m.get("name", "")
                m["kind"] = _infer_kind(parts[-1] if parts else nc)
            return {
                "metrics": result.get("metrics", []),
                "rejected_candidates": rejected + result.get("rejected_candidates", []),
            }
        except Exception:
            pass  # fall through to heuristic output

    # Heuristic-only fallback
    heuristic: list[dict] = []
    for c in candidates:
        col_word = c["column"].replace("_", " ").title()
        additivity = c["additivity"]
        heuristic.append({
            "name": col_word,
            "definition": f"{additivity.title()} additive measure from {c['dataset']}",
            "sql_expression": f"SUM({c['column']})" if additivity == "full" else c["column"],
            "numerator_columns": [c["fqn"]],
            "denominator_columns": [],
            "grain": c["grain_hint"],
            "aggregation": "sum" if additivity == "full" else "last_value",
            "additivity": additivity,
            "kind": _infer_kind(c["column"]),
            "good_direction": "up",
            "suggested_owner_role": "",
            "guardrail_for": None,
            "cadence": "daily",
            "confidence": 0.60,
            "reasoning": "Identified as measure candidate by column naming conventions",
            "source_column": c["fqn"],
            "dataset": c["dataset"],
            "display_name": col_word,
        })
    return {"metrics": heuristic, "rejected_candidates": rejected}


class ExpressionPreviewBody(PydanticBaseModel):
    dataset: str
    source_id: str
    expr_sql: str


@router.post("/metrics/evaluate-expression")
async def evaluate_expression(body: ExpressionPreviewBody, db: AsyncSession = Depends(get_db)) -> dict:
    """Run an aggregate expression against a warehouse dataset and return the scalar result.
    Does not require an existing metric. Used for expression preview during metric creation."""
    from dqt_server.models.core import Dataset, Source
    from dqt_server.check_runner import _make_adapter, _default_schema_for_source
    from dqt.adapters._protocol import AggExpr

    d = await db.get(Dataset, body.dataset)
    if d is None:
        raise HTTPException(404, detail=f"Dataset '{body.dataset}' not found")
    s = await db.get(Source, body.source_id)
    if s is None:
        raise HTTPException(404, detail=f"Source '{body.source_id}' not found")

    loop = asyncio.get_event_loop()

    def _run() -> dict:
        adapter = _make_adapter(s)
        if s.engine == "bigquery" and "." in body.dataset:
            schema, table = body.dataset.split(".", 1)
        else:
            schema = _default_schema_for_source(s) or d.schema_name or "public"
            table = body.dataset
        try:
            result = adapter.aggregate(schema, table, [AggExpr("result", body.expr_sql)])
            val = result.get("result")
            return {"value": float(val) if val is not None else None, "error": None}
        except Exception as exc:
            return {"value": None, "error": str(exc)}

    return await loop.run_in_executor(None, _run)


@router.post("/metrics/{fqn:path}/evaluate")
async def evaluate_metric(fqn: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Run the saved expression for an existing metric, store the result in metric_runs."""
    from dqt_server.models.core import Dataset, Source, MetricRun
    from dqt_server.check_runner import _make_adapter, _default_schema_for_source
    from dqt.adapters._protocol import AggExpr

    row = await db.get(MetricDefinition, fqn)
    if row is None:
        raise HTTPException(404, detail=f"Metric '{fqn}' not found")
    if not row.expr_sql or not row.source_id:
        raise HTTPException(400, detail="Metric has no expression or source configured")

    d = await db.get(Dataset, row.dataset)
    s = await db.get(Source, row.source_id)
    if d is None or s is None:
        raise HTTPException(400, detail="Dataset or source not found for this metric")

    loop = asyncio.get_event_loop()

    def _run() -> float | None:
        adapter = _make_adapter(s)
        if s.engine == "bigquery" and "." in row.dataset:
            schema, table = row.dataset.split(".", 1)
        else:
            schema = _default_schema_for_source(s) or d.schema_name or "public"
            table = row.dataset
        result = adapter.aggregate(schema, table, [AggExpr("result", row.expr_sql)])
        val = result.get("result")
        return float(val) if val is not None else None

    value = await loop.run_in_executor(None, _run)
    ran_at = datetime.now(timezone.utc)
    db.add(MetricRun(fqn=fqn, value=value, ran_at=ran_at))
    await db.commit()
    global _registry
    _registry = None
    return {"value": value, "ran_at": ran_at.isoformat()}


@router.delete("/metrics/{fqn:path}")
async def delete_metric(fqn: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)) -> dict:
    m = await db.get(MetricDefinition, fqn)
    if m is None:
        raise HTTPException(404, detail=f"Metric '{fqn}' not found")
    await db.delete(m)
    await db.commit()
    global _registry
    _registry = None
    background_tasks.add_task(_run_causality_in_background)
    return {"fqn": fqn, "deleted": True}


@router.get("/metrics/{fqn:path}/series")
async def metric_series(fqn: str, lookback_days: int = 30) -> list[dict]:
    """Return synthetic time series for the metric (weekly sinusoid + noise, seeded by fqn)."""
    import math
    import random

    rng = random.Random(hash(fqn) % 2**31)
    now = datetime.now(timezone.utc)
    result = []
    for i in range(lookback_days):
        dt = now - timedelta(days=lookback_days - i - 1)
        base = 0.87 + 0.08 * math.sin(2 * math.pi * i / 7)
        value = max(0.0, min(1.0, base + rng.gauss(0, 0.02)))
        verdict = "fail" if value < 0.70 else "warn" if value < 0.80 else "pass"
        result.append({"ts": dt.isoformat(), "value": round(value, 4), "verdict": verdict})
    return result


@router.get("/metrics/{fqn:path}/causal-edges")
async def get_causal_edges(fqn: str, db: AsyncSession = Depends(get_db)) -> list[dict]:
    """Return all causal edges where this metric is cause or effect."""
    from sqlalchemy import or_
    result = await db.execute(
        select(MetricCausalEdge).where(
            or_(MetricCausalEdge.cause_fqn == fqn, MetricCausalEdge.effect_fqn == fqn)
        ).order_by(MetricCausalEdge.evidence_strength.desc())
    )
    rows = list(result.scalars().all())
    return [
        {
            "id": r.id,
            "cause_fqn": r.cause_fqn,
            "effect_fqn": r.effect_fqn,
            "lag": r.lag,
            "p_value": r.p_value,
            "evidence_strength": r.evidence_strength,
            "shap_attribution": r.shap_attribution,
            "status": r.status,
            "computed_at": r.computed_at.isoformat(),
            "direction": "upstream" if r.effect_fqn == fqn else "downstream",
        }
        for r in rows
    ]


@router.get("/metrics/{fqn:path}/profile")
async def get_metric_profile(fqn: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Return descriptive stats, histogram, seasonality fingerprint, and known data issues."""
    import math
    import random
    import statistics

    # 91 days (13 weeks) of synthetic series, seeded by fqn
    rng = random.Random(hash(fqn) % 2**31)
    values: list[float] = []
    for i in range(91):
        base = 0.87 + 0.08 * math.sin(2 * math.pi * i / 7)
        values.append(max(0.0, min(1.0, base + rng.gauss(0, 0.02))))

    mean = statistics.mean(values)
    median = statistics.median(values)
    stddev = statistics.stdev(values)
    min_val = min(values)
    max_val = max(values)

    sorted_vals = sorted(values)
    n = len(sorted_vals)
    p25 = sorted_vals[max(0, int(n * 0.25) - 1)]
    p75 = sorted_vals[min(n - 1, int(n * 0.75))]
    cv = round(stddev / mean, 4) if mean != 0 else 0.0
    trailing_13w_mean = round(mean, 4)  # all 91 values = 13-week mean

    n_buckets = 20
    bucket_size = (max_val - min_val) / n_buckets if max_val > min_val else 1.0
    buckets = [0] * n_buckets
    for v in values:
        idx = min(int((v - min_val) / bucket_size), n_buckets - 1)
        buckets[idx] += 1
    histogram = [
        {"x": round(min_val + i * bucket_size, 4), "count": buckets[i]}
        for i in range(n_buckets)
    ]

    # Seasonality fingerprint — average value per day-of-week (Mon=0..Sun=6)
    start_dow = (datetime.now(timezone.utc) - timedelta(days=90)).weekday()
    dow_sums = [0.0] * 7
    dow_counts = [0] * 7
    for i, v in enumerate(values):
        dow = (start_dow + i) % 7
        dow_sums[dow] += v
        dow_counts[dow] += 1
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    seasonality = [
        {"day": day_names[d], "avg": round(dow_sums[d] / dow_counts[d], 4) if dow_counts[d] > 0 else 0.0}
        for d in range(7)
    ]

    # Known data issues — query actual check_runs for this metric's dataset
    from dqt_server.models.core import CheckRun
    known_data_issues: list[dict] = []
    row = await db.get(MetricDefinition, fqn)
    if row and row.dataset:
        result = await db.execute(
            select(CheckRun)
            .where(CheckRun.dataset_id == row.dataset, CheckRun.verdict.in_(["warn", "fail"]))
            .order_by(CheckRun.ran_at.desc())
            .limit(5)
        )
        for cr in result.scalars().all():
            known_data_issues.append({
                "detector": cr.detector_slug,
                "column": cr.column_name,
                "verdict": cr.verdict,
                "message": cr.plain_english or cr.detector_slug,
                "ran_at": cr.ran_at.isoformat() if cr.ran_at else None,
            })

    return {
        "mean": round(mean, 4),
        "median": round(median, 4),
        "stddev": round(stddev, 4),
        "min": round(min_val, 4),
        "max": round(max_val, 4),
        "p25": round(p25, 4),
        "p75": round(p75, 4),
        "cv": cv,
        "trailing_13w_mean": trailing_13w_mean,
        "count": len(values),
        "null_rate": 0.0,
        "histogram": histogram,
        "seasonality": seasonality,
        "known_data_issues": known_data_issues,
    }


@router.get("/metrics/{fqn:path}")
async def get_metric(fqn: str, db: AsyncSession = Depends(get_db)) -> dict:
    row = await db.get(MetricDefinition, fqn)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Metric '{fqn}' not found")
    m = _get_registry().get(fqn)
    return {
        "fqn": row.fqn,
        "display_name": row.display_name,
        "kind": row.kind,
        "dataset": row.dataset,
        "description": row.description or "",
        "owners": row.owners or [],
        "tags": row.tags or [],
        "grain": row.grain,
        "additivity": row.additivity,
        "good_direction": row.good_direction,
        "refresh_cadence": row.refresh_cadence,
        "lineage": row.lineage or [],
        "source_id": row.source_id,
        "column_name": row.column_name,
        "warn_threshold": row.warn_threshold,
        "fail_threshold": row.fail_threshold,
        "unit": m.unit if m else "",
        "current_value": m.current_value if m else None,
        "current_verdict": m.current_verdict if m else None,
        "last_run": m.last_run if m else None,
        "pinned": fqn in _pinned,
        "expr_type": row.expr_type,
        "expr_sql": row.expr_sql,
        "numerator_sql": row.numerator_sql,
        "denominator_sql": row.denominator_sql,
        "filter_sql": row.filter_sql,
        "time_column": row.time_column,
    }


@router.post("/metrics/{fqn:path}/pin")
async def pin_metric(fqn: str) -> dict:
    _pinned.add(fqn)
    return {"fqn": fqn, "pinned": True}


@router.post("/metrics/{fqn:path}/explain")
async def explain_metric_sse(fqn: str, request: Request) -> StreamingResponse:
    """Stream a MovementExplanation in 5 SSE chunks. Results cached 6h."""
    registry = _get_registry()
    metric = registry.get(fqn)
    if metric is None:
        raise HTTPException(status_code=404, detail=f"Metric '{fqn}' not found")

    body = await request.json() if await request.body() else {}
    lookback_days = int(body.get("lookback_days", 7))
    force_refresh = bool(body.get("force_refresh", False))

    async def event_stream():
        from dqt.insights.explain import explain_movement
        from dqt.store.memory import MemoryStore

        now = datetime.now(timezone.utc)
        window_start = now - timedelta(days=lookback_days)

        store = MemoryStore()

        def _emit(event_type: str, data: dict) -> str:
            return f"data: {_json.dumps({'type': event_type, **data})}\n\n"

        yield _emit("start", {"fqn": fqn, "window_start": window_start.isoformat(),
                               "window_end": now.isoformat()})
        await asyncio.sleep(0)

        # Return cached result if available and not forcing refresh
        cached = None if force_refresh else _cache_get(fqn, lookback_days)
        if cached:
            yield _emit("summary", cached["summary"])
            await asyncio.sleep(0)
            yield _emit("channel_a", cached["channel_a"])
            await asyncio.sleep(0)
            yield _emit("channel_b", cached["channel_b"])
            await asyncio.sleep(0)
            yield _emit("ruled_out", cached["ruled_out"])
            await asyncio.sleep(0)
            yield _emit("done", cached["done"])
            return

        try:
            expl = explain_movement(
                fqn, (window_start, now),
                store=store,
                use_llm=True,
            )
            summary_chunk = {"text": expl.summary_paragraph, "primary_channel": expl.primary_channel}
            channel_a_chunk = {
                "issues": [
                    {"detector_slug": i.detector_slug, "verdict": i.verdict,
                     "contribution_low": i.contribution_low, "contribution_high": i.contribution_high,
                     "plain_english": i.evidence.detail.get("plain_english", "")}
                    for i in expl.data_issues
                ],
                "estimated_contribution": list(expl.estimated_data_contribution),
            }
            channel_b_chunk = {
                "drivers": [
                    {"cause": d.cause_metric_fqn, "lag": d.lag_periods,
                     "p_value": d.p_value, "evidence_strength": d.evidence_strength,
                     "contribution_low": d.contribution_low, "contribution_high": d.contribution_high}
                    for d in expl.business_drivers
                ],
                "estimated_contribution": list(expl.estimated_business_contribution),
            }
            ruled_out_chunk = {
                "items": [{"fqn": r.candidate_fqn, "reason": r.reason} for r in expl.ruled_out]
            }
            done_chunk = {
                "explanation_id": str(expl.explanation_id),
                "citations": {k: [e.row_id for e in rows] for k, rows in expl.citations.items()},
            }

            _cache_set(fqn, lookback_days, {
                "summary": summary_chunk,
                "channel_a": channel_a_chunk,
                "channel_b": channel_b_chunk,
                "ruled_out": ruled_out_chunk,
                "done": done_chunk,
            })

            yield _emit("summary", summary_chunk)
            await asyncio.sleep(0)
            yield _emit("channel_a", channel_a_chunk)
            await asyncio.sleep(0)
            yield _emit("channel_b", channel_b_chunk)
            await asyncio.sleep(0)
            yield _emit("ruled_out", ruled_out_chunk)
            await asyncio.sleep(0)
            yield _emit("done", done_chunk)

        except Exception as exc:
            yield _emit("error", {"message": str(exc)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
