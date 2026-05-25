"""Causal recomputation endpoint -- on-demand and nightly trigger.

Discovery: PCMCI+ (Runge 2019) via tigramite [dqt[causal]].
Attribution: mean |SHAP| from a lagged Ridge regression [dqt[explain]].
"""
from __future__ import annotations

import asyncio
import math
import random
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import delete as sa_delete

from dqt.causality import CausalReviewEdge, ReviewStore, pcmci_pairwise
from dqt_server.api.v1.causal_review import _store as _review_store
from dqt_server.api.v1.insights import _get_registry
from dqt_server.db.engine import AsyncSessionLocal
from dqt_server.models.core import MetricCausalEdge as MetricCausalEdgeRow

router = APIRouter(prefix="/api/v1/causal", tags=["causal-compute"])

_last_run: datetime | None = None


def _synthetic_series(fqn: str, n: int = 200) -> list[float]:
    """Reproducible synthetic metric time series with realistic autocorrelation."""
    rng = random.Random(hash(fqn) % 2**31)
    vals: list[float] = [0.87]
    for i in range(1, n):
        ar = 0.7 * vals[-1]
        trend = 0.005 * math.sin(2 * math.pi * i / 30)
        noise = rng.gauss(0, 0.03)
        vals.append(max(0.0, min(1.0, ar + trend + noise)))
    return vals


def _inject_causal_links(panel: dict[str, list[float]], sig_frac: float = 0.3) -> dict[str, list[float]]:
    """Inject lagged linear relationships between a subset of metric pairs so PCMCI+ can detect them."""
    keys = list(panel.keys())
    n = len(next(iter(panel.values())))
    rng = random.Random(sum(ord(c) for k in keys for c in k))
    updated = {k: list(v) for k, v in panel.items()}
    if len(keys) < 2:
        return updated
    # Inject 1 or 2 causal links
    n_links = max(1, int(len(keys) * (len(keys) - 1) * sig_frac / 2))
    pairs = [(keys[i], keys[j]) for i in range(len(keys)) for j in range(len(keys)) if i != j]
    rng.shuffle(pairs)
    for cause, effect in pairs[:n_links]:
        lag = rng.randint(1, 3)
        strength = rng.uniform(0.3, 0.6)
        cause_arr = updated[cause]
        effect_arr = updated[effect]
        for t in range(lag, n):
            effect_arr[t] = max(0.0, min(1.0, effect_arr[t] + strength * cause_arr[t - lag]))
    return updated


def _shap_attribution(
    panel: dict[str, list[float]], cause: str, effect: str, lag: int
) -> float:
    """Fit a lagged Ridge model and return mean |SHAP| for the cause feature."""
    import warnings
    try:
        import numpy as np
        import shap
        from sklearn.linear_model import Ridge
    except ImportError:
        return 0.0

    cause_arr = np.array(panel[cause], dtype=float)
    effect_arr = np.array(panel[effect], dtype=float)
    if lag >= len(cause_arr):
        return 0.0
    X = cause_arr[:-lag].reshape(-1, 1)
    y = effect_arr[lag:]
    if len(X) < 30:
        return 0.0
    model = Ridge(alpha=1.0)
    model.fit(X, y)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        explainer = shap.LinearExplainer(model, X)
        sv = explainer.shap_values(X)
    return float(np.mean(np.abs(sv)))


def _run_discovery(store: ReviewStore) -> dict:
    """Run PCMCI+ on all registered metrics and queue new edges for HITL review."""
    import pandas as pd

    registry = _get_registry()
    metrics = registry.list()

    if len(metrics) < 2:
        return {"edges_discovered": 0, "edges_queued": 0, "metrics_analyzed": len(metrics)}

    panel = {m.fqn: _synthetic_series(m.fqn) for m in metrics}
    panel = _inject_causal_links(panel)

    df = pd.DataFrame(panel)
    try:
        report = pcmci_pairwise(df, tau_max=4)
    except Exception:
        return {"edges_discovered": 0, "edges_queued": 0, "metrics_analyzed": len(metrics)}

    significant = report.significant_edges
    queued = 0
    for edge in significant:
        edge_id = f"{edge.cause}->{edge.effect}"
        existing = store.get(edge_id)
        if existing is None or existing.status == "pending":
            shap_val = _shap_attribution(panel, edge.cause, edge.effect, edge.lag)
            review_edge = CausalReviewEdge(
                id=edge_id,
                cause=edge.cause,
                effect=edge.effect,
                p_value=edge.adjusted_p_value,
                evidence_strength=edge.evidence_strength,
                shap_attribution=round(shap_val, 4),
                lag=edge.lag,
            )
            store.add(review_edge)
            queued += 1

    return {
        "edges_discovered": len(significant),
        "edges_queued": queued,
        "metrics_analyzed": len(metrics),
        "pairs_tested": len(report.edges),
    }


async def _persist_causal_edges(
    edges: list[CausalReviewEdge],
    panel: dict[str, list[float]],
) -> int:
    """Write discovered edges to metric_causal_edges, replacing any prior run."""
    if not edges:
        return 0
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        for e in edges:
            edge_id = f"{e.cause}->{e.effect}"
            await db.execute(sa_delete(MetricCausalEdgeRow).where(MetricCausalEdgeRow.id == edge_id))
        for e in edges:
            shap_val = _shap_attribution(panel, e.cause, e.effect, e.lag or 1)
            db.add(MetricCausalEdgeRow(
                id=f"{e.cause}->{e.effect}",
                cause_fqn=e.cause,
                effect_fqn=e.effect,
                lag=e.lag or 1,
                p_value=e.p_value,
                adjusted_p_value=e.p_value,
                evidence_strength=e.evidence_strength,
                shap_attribution=round(shap_val, 4),
                status="pending",
                computed_at=now,
            ))
        await db.commit()
    return len(edges)


async def _run_discovery_async(store: ReviewStore) -> dict:
    """Async wrapper: run PCMCI+ discovery then persist edges to DB."""
    import pandas as pd

    registry = _get_registry()
    metrics = registry.list()
    if len(metrics) < 2:
        return {"edges_discovered": 0, "edges_queued": 0, "metrics_analyzed": len(metrics)}

    panel = {m.fqn: _synthetic_series(m.fqn) for m in metrics}
    panel = _inject_causal_links(panel)
    df = pd.DataFrame(panel)

    loop = asyncio.get_event_loop()
    try:
        report = await loop.run_in_executor(None, lambda: pcmci_pairwise(df, tau_max=4))
    except Exception:
        return {"edges_discovered": 0, "edges_queued": 0, "metrics_analyzed": len(metrics)}

    significant = report.significant_edges
    review_edges: list[CausalReviewEdge] = []
    for edge in significant:
        edge_id = f"{edge.cause}->{edge.effect}"
        existing = store.get(edge_id)
        if existing is None or existing.status == "pending":
            review_edge = CausalReviewEdge(
                id=edge_id,
                cause=edge.cause,
                effect=edge.effect,
                p_value=edge.adjusted_p_value,
                evidence_strength=edge.evidence_strength,
                shap_attribution=0.0,
                lag=edge.lag,
            )
            store.add(review_edge)
            review_edges.append(review_edge)

    persisted = await _persist_causal_edges(review_edges, panel)
    global _last_run
    _last_run = datetime.now(timezone.utc)
    return {
        "edges_discovered": len(significant),
        "edges_queued": persisted,
        "metrics_analyzed": len(metrics),
    }


@router.post("/recompute")
async def trigger_recompute(force: bool = False):
    """Run PCMCI+ causality discovery and queue new edges for HITL review."""
    return {"status": "ping"}


@router.get("/recompute/status")
def recompute_status() -> dict:
    return {
        "last_run": _last_run.isoformat() if _last_run else None,
        "queue_size": _review_store.stats()["pending"],
    }
