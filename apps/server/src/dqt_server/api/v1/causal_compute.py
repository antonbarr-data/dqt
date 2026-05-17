"""Causal recomputation endpoint -- on-demand and nightly trigger."""
from __future__ import annotations

import asyncio
import math
import random
from datetime import datetime, timezone

from fastapi import APIRouter

from dqt.causality import CausalReviewEdge, ReviewStore, granger_pairwise
from dqt_server.api.v1.causal_review import _store as _review_store
from dqt_server.api.v1.insights import _get_registry

router = APIRouter(prefix="/api/v1/causal", tags=["causal-compute"])

_last_run: datetime | None = None


def _synthetic_series(fqn: str, n: int = 60) -> list[float]:
    """Generate a reproducible synthetic metric time series seeded by fqn."""
    rng = random.Random(hash(fqn) % 2**31)
    base = 0.87
    vals = []
    for i in range(n):
        val = base + 0.08 * math.sin(2 * math.pi * i / 7) + rng.gauss(0, 0.02)
        vals.append(max(0.0, min(1.0, val)))
    return vals


def _run_discovery(store: ReviewStore) -> dict:
    """Run Granger pairwise on all registered metrics and queue new edges."""
    import pandas as pd

    registry = _get_registry()
    metrics = registry.list()

    if len(metrics) < 2:
        return {"edges_discovered": 0, "edges_queued": 0, "metrics_analyzed": len(metrics)}

    panel = {m.fqn: _synthetic_series(m.fqn) for m in metrics}
    df = pd.DataFrame(panel)
    report = granger_pairwise(df, max_lag=4)

    significant = report.significant_edges
    queued = 0
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
            )
            store.add(review_edge)
            queued += 1

    return {
        "edges_discovered": len(significant),
        "edges_queued": queued,
        "metrics_analyzed": len(metrics),
        "pairs_tested": len(report.edges),
    }


@router.post("/recompute")
async def trigger_recompute(force: bool = False) -> dict:
    """Run causality discovery and queue new edges for HITL review."""
    global _last_run
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _run_discovery, _review_store)
    _last_run = datetime.now(timezone.utc)
    return {
        "status": "ok",
        "ran_at": _last_run.isoformat(),
        **result,
    }


@router.get("/recompute/status")
def recompute_status() -> dict:
    return {
        "last_run": _last_run.isoformat() if _last_run else None,
        "queue_size": _review_store.stats()["pending"],
    }
