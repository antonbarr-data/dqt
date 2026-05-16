"""Insights router -- metric list, detail, series, and pin endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

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
    """Return time series snapshots for the metric (empty list when no data stored)."""
    return []


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
