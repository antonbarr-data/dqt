"""Lineage API -- DB-backed edge store, dbt manifest import."""
from __future__ import annotations

import json
import uuid
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from dqt_server.db.engine import get_db
from dqt_server.models.core import LineageEdgeRecord

router = APIRouter(prefix="/api/v1/lineage", tags=["lineage"])


class NodeOut(BaseModel):
    id: str
    kind: str
    label: str
    dataset: str = ""
    column: str = ""


class EdgeOut(BaseModel):
    id: str
    source: str
    target: str
    kind: str
    lag_weeks: int = 0
    confidence: float
    description: str = ""


class GraphOut(BaseModel):
    nodes: list[NodeOut]
    edges: list[EdgeOut]
    root: str | None
    direction: str
    depth: int


class EdgeCreateIn(BaseModel):
    upstream_node: str
    upstream_label: str = ""
    downstream_node: str
    downstream_label: str = ""
    kind: str = "column_lineage"
    confidence: float = 1.0


def _records_to_graph(records: list[LineageEdgeRecord], root: str | None, direction: str, depth: int) -> GraphOut:
    """Build a GraphOut from edge records, optionally sub-graphed from a root node."""
    all_edges = [
        EdgeOut(
            id=r.id,
            source=r.upstream_node,
            target=r.downstream_node,
            kind=r.kind,
            confidence=r.confidence,
        )
        for r in records
    ]

    if root is not None:
        # BFS from root up to depth
        visited: set[str] = set()
        frontier = {root}
        for _ in range(depth):
            next_frontier: set[str] = set()
            for nid in frontier:
                if direction in ("downstream", "both"):
                    for e in all_edges:
                        if e.source == nid and e.target not in visited:
                            next_frontier.add(e.target)
                if direction in ("upstream", "both"):
                    for e in all_edges:
                        if e.target == nid and e.source not in visited:
                            next_frontier.add(e.source)
            visited |= frontier
            frontier = next_frontier - visited
        visited |= frontier
        all_edges = [e for e in all_edges if e.source in visited and e.target in visited]

    # Collect node ids from edges + root
    node_ids: set[str] = set()
    for e in all_edges:
        node_ids.add(e.source)
        node_ids.add(e.target)
    if root:
        node_ids.add(root)

    # Build label map from records
    label_map: dict[str, str] = {}
    for r in records:
        label_map[r.upstream_node] = r.upstream_label or r.upstream_node
        label_map[r.downstream_node] = r.downstream_label or r.downstream_node

    nodes = [
        NodeOut(id=nid, kind="metric", label=label_map.get(nid, nid))
        for nid in node_ids
    ]

    return GraphOut(nodes=nodes, edges=all_edges, root=root, direction=direction, depth=depth)


@router.get("/graph", response_model=GraphOut)
async def lineage_graph(
    root: str | None = Query(None),
    direction: str = Query("both"),
    depth: int = Query(3, ge=1, le=5),
    include_causal: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    if direction not in ("downstream", "upstream", "both"):
        raise HTTPException(status_code=422, detail="direction must be downstream, upstream, or both")
    result = await db.execute(select(LineageEdgeRecord))
    records = list(result.scalars().all())
    if not include_causal:
        records = [r for r in records if r.kind != "causality"]
    return _records_to_graph(records, root, direction, depth)


@router.get("/path")
async def lineage_path(
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(LineageEdgeRecord))
    records = list(result.scalars().all())
    adj: dict[str, list[str]] = {}
    for r in records:
        adj.setdefault(r.upstream_node, []).append(r.downstream_node)

    # BFS
    queue = [from_]
    came_from: dict[str, str | None] = {from_: None}
    while queue:
        node = queue.pop(0)
        if node == to:
            path = []
            cur: str | None = to
            while cur is not None:
                path.append(cur)
                cur = came_from[cur]
            path.reverse()
            return {"path": path, "length": len(path) - 1}
        for nxt in adj.get(node, []):
            if nxt not in came_from:
                came_from[nxt] = node
                queue.append(nxt)
    raise HTTPException(status_code=404, detail="No path found")


@router.post("/edges", status_code=201, response_model=EdgeOut)
async def create_edge(body: EdgeCreateIn, db: AsyncSession = Depends(get_db)):
    edge_id = str(uuid.uuid4())
    record = LineageEdgeRecord(
        id=edge_id,
        upstream_node=body.upstream_node,
        upstream_label=body.upstream_label or body.upstream_node,
        downstream_node=body.downstream_node,
        downstream_label=body.downstream_label or body.downstream_node,
        kind=body.kind,
        confidence=body.confidence,
    )
    db.add(record)
    await db.commit()
    return EdgeOut(
        id=edge_id,
        source=body.upstream_node,
        target=body.downstream_node,
        kind=body.kind,
        confidence=body.confidence,
    )


@router.delete("/edges/{edge_id}", status_code=204)
async def delete_edge(edge_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LineageEdgeRecord).where(LineageEdgeRecord.id == edge_id))
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Edge not found")
    await db.execute(delete(LineageEdgeRecord).where(LineageEdgeRecord.id == edge_id))
    await db.commit()


@router.post("/import-dbt", status_code=201)
async def import_dbt_manifest(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Import lineage edges from a dbt manifest.json file."""
    content = await file.read()
    try:
        manifest = json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {e}")

    nodes: dict = manifest.get("nodes", {})
    sources: dict = manifest.get("sources", {})

    # Build label map: unique_id -> friendly name
    label_map: dict[str, str] = {}
    for uid, node in nodes.items():
        label_map[uid] = node.get("name", uid)
    for uid, src in sources.items():
        source_name = src.get("source_name", "")
        table_name = src.get("name", uid)
        label_map[uid] = f"{source_name}.{table_name}" if source_name else table_name

    created = 0
    errors = []
    for uid, node in nodes.items():
        if node.get("resource_type") not in ("model", "snapshot", "analysis"):
            continue
        deps = node.get("depends_on", {}).get("nodes", [])
        node_label = label_map.get(uid, uid.split(".")[-1])
        for dep_uid in deps:
            dep_label = label_map.get(dep_uid, dep_uid.split(".")[-1])
            # Deduplicate: check if edge already exists
            existing = await db.execute(
                select(LineageEdgeRecord).where(
                    LineageEdgeRecord.upstream_node == dep_uid,
                    LineageEdgeRecord.downstream_node == uid,
                )
            )
            if existing.scalar_one_or_none() is not None:
                continue
            record = LineageEdgeRecord(
                id=str(uuid.uuid4()),
                upstream_node=dep_uid,
                upstream_label=dep_label,
                downstream_node=uid,
                downstream_label=node_label,
                kind="dbt",
                confidence=1.0,
            )
            db.add(record)
            created += 1

    await db.commit()
    return {"imported": created, "errors": errors}
