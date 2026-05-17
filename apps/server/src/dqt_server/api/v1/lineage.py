# apps/server/src/dqt_server/api/v1/lineage.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from dqt.lineage import LineageGraph, LineageNode, LineageEdge

router = APIRouter(prefix="/api/v1/lineage", tags=["lineage"])


def _build_demo_graph() -> LineageGraph:
    g = LineageGraph()
    nodes = [
        LineageNode(id="marketing.spend_usd", kind="metric", label="Marketing Spend"),
        LineageNode(id="marketing.impressions", kind="metric", label="Impressions"),
        LineageNode(id="marketing.clicks", kind="metric", label="Clicks"),
        LineageNode(id="product.signups", kind="metric", label="Signups"),
        LineageNode(id="product.activation_rate", kind="metric", label="Activation Rate"),
        LineageNode(id="revenue.gmv", kind="metric", label="GMV"),
        LineageNode(id="revenue.net_revenue", kind="metric", label="Net Revenue"),
        LineageNode(id="ops.fulfillment_rate", kind="metric", label="Fulfillment Rate"),
        LineageNode(id="ops.support_tickets", kind="metric", label="Support Tickets"),
    ]
    for n in nodes:
        g.add_node(n)
    edges = [
        LineageEdge(source="marketing.spend_usd", target="marketing.impressions", kind="column_lineage"),
        LineageEdge(source="marketing.impressions", target="marketing.clicks", kind="column_lineage"),
        LineageEdge(source="marketing.clicks", target="product.signups", kind="column_lineage"),
        LineageEdge(source="product.signups", target="product.activation_rate", kind="column_lineage"),
        LineageEdge(source="product.activation_rate", target="revenue.gmv", kind="column_lineage"),
        LineageEdge(source="ops.fulfillment_rate", target="revenue.gmv", kind="column_lineage"),
        LineageEdge(source="revenue.gmv", target="revenue.net_revenue", kind="column_lineage"),
        LineageEdge(source="ops.support_tickets", target="ops.fulfillment_rate", kind="causality", confidence=0.72),
        LineageEdge(source="marketing.clicks", target="revenue.gmv", kind="causality", confidence=0.61),
    ]
    for e in edges:
        g.add_edge(e)
    return g


_DEMO_GRAPH = _build_demo_graph()


class NodeOut(BaseModel):
    id: str
    kind: str
    label: str
    dataset: str
    column: str


class EdgeOut(BaseModel):
    source: str
    target: str
    kind: str
    lag_weeks: int
    confidence: float
    description: str


class GraphOut(BaseModel):
    nodes: list[NodeOut]
    edges: list[EdgeOut]
    root: str
    direction: str
    depth: int


@router.get("/graph", response_model=GraphOut)
def lineage_graph(
    root: str = Query(..., description="Root node id"),
    direction: str = Query("both", description="downstream | upstream | both"),
    depth: int = Query(3, ge=1, le=5),
    include_causal: bool = Query(True),
):
    if direction not in ("downstream", "upstream", "both"):
        raise HTTPException(status_code=422, detail="direction must be downstream, upstream, or both")
    sg = _DEMO_GRAPH.subgraph(root, direction=direction, depth=depth)
    edges = sg.edges
    if not include_causal:
        edges = [e for e in edges if e.kind != "causality"]
    return GraphOut(
        nodes=[NodeOut(id=n.id, kind=n.kind, label=n.label, dataset=n.dataset, column=n.column) for n in sg.nodes],
        edges=[EdgeOut(source=e.source, target=e.target, kind=e.kind, lag_weeks=e.lag_weeks, confidence=e.confidence, description=e.description) for e in edges],
        root=root,
        direction=direction,
        depth=depth,
    )


@router.get("/path")
def lineage_path(
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
):
    path = _DEMO_GRAPH.shortest_path(from_, to)
    if path is None:
        raise HTTPException(status_code=404, detail="No path found")
    return {"path": path, "length": len(path) - 1}
