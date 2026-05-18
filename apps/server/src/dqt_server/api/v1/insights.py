"""Insights router -- metric list, detail, series, pin, and explain endpoints."""
from __future__ import annotations

import asyncio
import json as _json
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dqt_server.db.engine import get_db
from dqt_server.models.core import MetricDefinition

from dqt.metrics import Metric, MetricKind, MetricRegistry

router = APIRouter(prefix="/api/v1", tags=["insights"])

_pinned: set[str] = set()
_registry: MetricRegistry | None = None


def _run_causality_in_background() -> None:
    """Lazy-import causal modules and trigger discovery. Safe to call after all modules load."""
    try:
        from dqt_server.api.v1.causal_compute import _run_discovery
        from dqt_server.api.v1.causal_review import _store as _review_store
        _run_discovery(_review_store)
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
                created_at=datetime.now(timezone.utc),
            ))
            created += 1
    await db.commit()
    global _registry
    _registry = None
    if created > 0:
        background_tasks.add_task(_run_causality_in_background)
    return {"created": created}


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


@router.get("/metrics/{fqn:path}")
async def get_metric(fqn: str) -> dict:
    metric = _get_registry().get(fqn)
    if metric is None:
        raise HTTPException(status_code=404, detail=f"Metric '{fqn}' not found")
    return _metric_to_dict(metric)


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
