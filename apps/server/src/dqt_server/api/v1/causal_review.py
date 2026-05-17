# apps/server/src/dqt_server/api/v1/causal_review.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from dqt.causality.review import CausalReviewEdge, ReviewStore

router = APIRouter(prefix="/api/v1/causal/review", tags=["causal-review"])

_store = ReviewStore()


def _seed() -> None:
    demo_edges = [
        CausalReviewEdge(id="marketing.clicks->revenue.gmv", cause="marketing.clicks", effect="revenue.gmv", p_value=0.008, evidence_strength="strong"),
        CausalReviewEdge(id="ops.support_tickets->ops.fulfillment_rate", cause="ops.support_tickets", effect="ops.fulfillment_rate", p_value=0.023, evidence_strength="moderate"),
        CausalReviewEdge(id="product.signups->revenue.gmv", cause="product.signups", effect="revenue.gmv", p_value=0.041, evidence_strength="moderate"),
        CausalReviewEdge(id="marketing.impressions->product.signups", cause="marketing.impressions", effect="product.signups", p_value=0.067, evidence_strength="weak"),
        CausalReviewEdge(id="ops.fulfillment_rate->revenue.net_revenue", cause="ops.fulfillment_rate", effect="revenue.net_revenue", p_value=0.003, evidence_strength="strong"),
    ]
    for e in demo_edges:
        _store.add(e)


_seed()


class ReviewEdgeOut(BaseModel):
    id: str
    cause: str
    effect: str
    p_value: float
    evidence_strength: str
    status: str
    reviewer: str
    notes: str


class ReviewDecisionIn(BaseModel):
    decision: str   # "accept" | "reject"
    reviewer: str
    notes: str = ""


class StatsOut(BaseModel):
    total: int
    pending: int
    accepted: int
    rejected: int
    accept_rate: float


@router.get("/queue", response_model=list[ReviewEdgeOut])
def get_queue(
    status: str = Query("pending"),
    limit: int = Query(20, ge=1, le=100),
):
    if status == "pending":
        edges = _store.list_pending(limit=limit)
    else:
        edges = _store.list_by_status(status)[:limit]
    return [ReviewEdgeOut(**e.__dict__) for e in edges]


@router.post("/{edge_id}", response_model=ReviewEdgeOut)
def post_review(edge_id: str, body: ReviewDecisionIn):
    if body.decision not in ("accept", "reject"):
        raise HTTPException(status_code=422, detail="decision must be accept or reject")
    try:
        edge = _store.review(edge_id, decision=body.decision, reviewer=body.reviewer, notes=body.notes)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Edge {edge_id!r} not found")
    return ReviewEdgeOut(**edge.__dict__)


@router.get("/stats", response_model=StatsOut)
def get_stats():
    return StatsOut(**_store.stats())
