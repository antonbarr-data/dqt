"""Insights router -- metric list, detail, series, pin, and explain endpoints."""
from __future__ import annotations

import asyncio
import json as _json
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from dqt.metrics import Metric, MetricKind, MetricRegistry
from dqt_server.gigler_service import GIGLER_SOURCE_ID, GIGLER_TABLES

router = APIRouter(prefix="/api/v1", tags=["insights"])

_pinned: set[str] = set()
_registry: MetricRegistry | None = None


def _get_registry() -> MetricRegistry:
    global _registry
    if _registry is None:
        _registry = _build_registry()
    return _registry


def _build_registry() -> MetricRegistry:
    metrics = [
        Metric(
            fqn=f"{GIGLER_SOURCE_ID}.default.{table}.quality",
            display_name=f"{table} quality",
            kind="ratio",
            dataset=table,
            description=f"Overall data quality score for {table}",
            owners=["data-team"],
            tags=["gigler", "quality"],
        )
        for table in GIGLER_TABLES
    ]
    return MetricRegistry(metrics)


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
async def list_metrics() -> list[dict]:
    return [_metric_to_dict(m) for m in _get_registry().list()]


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
    """Stream a MovementExplanation in 5 SSE chunks."""
    registry = _get_registry()
    metric = registry.get(fqn)
    if metric is None:
        raise HTTPException(status_code=404, detail=f"Metric '{fqn}' not found")

    body = await request.json() if await request.body() else {}
    lookback_days = int(body.get("lookback_days", 7))

    async def event_stream():
        from dqt.insights.explain import explain_movement
        from dqt.store.memory import MemoryStore

        now = datetime.now(timezone.utc)
        window_start = now - timedelta(days=lookback_days)

        # Use an in-memory store for now (no Postgres wired in this endpoint yet)
        store = MemoryStore()

        def _emit(event_type: str, data: dict) -> str:
            return f"data: {_json.dumps({'type': event_type, **data})}\n\n"

        yield _emit("start", {"fqn": fqn, "window_start": window_start.isoformat(),
                               "window_end": now.isoformat()})
        await asyncio.sleep(0)

        try:
            expl = explain_movement(
                fqn, (window_start, now),
                store=store,
                use_llm=True,
            )
            yield _emit("summary", {"text": expl.summary_paragraph,
                                     "primary_channel": expl.primary_channel})
            await asyncio.sleep(0)

            yield _emit("channel_a", {
                "issues": [
                    {"detector_slug": i.detector_slug, "verdict": i.verdict,
                     "contribution_low": i.contribution_low, "contribution_high": i.contribution_high,
                     "plain_english": i.evidence.detail.get("plain_english", "")}
                    for i in expl.data_issues
                ],
                "estimated_contribution": list(expl.estimated_data_contribution),
            })
            await asyncio.sleep(0)

            yield _emit("channel_b", {
                "drivers": [
                    {"cause": d.cause_metric_fqn, "lag": d.lag_periods,
                     "p_value": d.p_value, "evidence_strength": d.evidence_strength,
                     "contribution_low": d.contribution_low, "contribution_high": d.contribution_high}
                    for d in expl.business_drivers
                ],
                "estimated_contribution": list(expl.estimated_business_contribution),
            })
            await asyncio.sleep(0)

            yield _emit("ruled_out", {
                "items": [{"fqn": r.candidate_fqn, "reason": r.reason} for r in expl.ruled_out]
            })
            await asyncio.sleep(0)

            yield _emit("done", {
                "explanation_id": str(expl.explanation_id),
                "citations": {k: [e.row_id for e in rows] for k, rows in expl.citations.items()},
            })

        except Exception as exc:
            yield _emit("error", {"message": str(exc)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
