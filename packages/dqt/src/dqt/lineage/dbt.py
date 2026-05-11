"""dbt manifest.json ingestion for table- and column-level lineage.
Ref: https://docs.getdbt.com/reference/artifacts/manifest-json (format v10+)
Column-level edges use sqlglot.lineage (optional; degrades to table-level if unavailable).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from dqt.lineage.models import LineageEdge, LineageGraph, LineageNode

_log = logging.getLogger(__name__)


def _column_edges_from_compiled_sql(
    compiled_sql: str,
    dep_nodes: list[tuple[str, str]],  # [(unique_id, dataset_name), ...]
    target_unique_id: str,
    known_col_node_ids: set[str],
) -> list[LineageEdge]:
    """Return column-level LineageEdges derived from compiled SQL via sqlglot.lineage.

    For each output column of the model, sqlglot.lineage traces it to a leaf
    Table node whose name is ``table_alias.column``.  We match the table name
    against dep_nodes to resolve the dbt unique_id, then emit an edge from
    ``<dep_unique_id>.<col>`` to ``<target_unique_id>.<col>`` when both column
    nodes are known in the graph.

    Returns [] if sqlglot is unavailable or parsing fails.
    """
    try:
        import sqlglot.expressions as exp
        from sqlglot.lineage import lineage as sqlglot_lineage
    except ImportError:
        return []

    # Build a name→unique_id lookup (lower-cased for case-insensitive matching).
    name_to_dep: dict[str, str] = {name.lower(): uid for uid, name in dep_nodes}

    results: list[LineageEdge] = []
    try:
        col_nodes = sqlglot_lineage(None, compiled_sql)
    except Exception as exc:
        _log.debug("sqlglot.lineage failed for %s: %s", target_unique_id, exc)
        return []

    for tgt_col, root_node in col_nodes.items():
        tgt_col_id = f"{target_unique_id}.{tgt_col}"
        if tgt_col_id not in known_col_node_ids:
            continue

        for node in root_node.walk():
            # Leaf nodes have a Table expression as their source.
            if not isinstance(node.source, exp.Table):
                continue
            # Use the actual table name (not the alias) from the Table expression.
            # node.name == "table_alias_or_name.column_name"
            table_name = node.source.name.lower()  # e.g. "raw_orders" or "orders"
            dep_uid = name_to_dep.get(table_name)
            if dep_uid is None:
                continue
            # Column name is the last part of node.name (after the dot).
            parts = node.name.split(".", 1)
            if len(parts) != 2:
                continue
            src_col = parts[1]
            src_col_id = f"{dep_uid}.{src_col}"
            if src_col_id not in known_col_node_ids:
                continue
            results.append(LineageEdge(
                source=src_col_id,
                target=tgt_col_id,
                kind="column_derived_from",
                confidence=0.8,
            ))

    return results


def from_dbt_manifest(manifest_path: str | Path) -> LineageGraph:
    """Parse a dbt manifest.json and return a LineageGraph with table- and column-level edges.

    Column-level lineage is extracted from ``compiled_code`` when present,
    using ``sqlglot.lineage``. Degrades to table-level if sqlglot is unavailable
    or the model has no compiled SQL.

    Example::

        graph = from_dbt_manifest("target/manifest.json")
        col_nodes = [n for n in graph.nodes if n.kind == "column"]
        col_edges = [e for e in graph.edges if e.kind == "column_derived_from"]
    """
    path = Path(manifest_path)
    manifest: dict = json.loads(path.read_text(encoding="utf-8"))

    graph = LineageGraph()
    seen_node_ids: set[str] = set()

    all_entries: dict[str, dict] = {}
    all_entries.update(manifest.get("nodes", {}))
    all_entries.update(manifest.get("sources", {}))

    _WANTED = {"model", "source"}

    # --- Pass 1: dataset nodes + column nodes ---
    for unique_id, node in all_entries.items():
        if node.get("resource_type", "") not in _WANTED:
            continue
        name = node.get("name", unique_id)
        graph.add_node(LineageNode(id=unique_id, kind="dataset", label=name, dataset=name))
        seen_node_ids.add(unique_id)

        for col_name in node.get("columns", {}).keys():
            col_node_id = f"{unique_id}.{col_name}"
            graph.add_node(LineageNode(
                id=col_node_id, kind="column", label=col_name,
                dataset=name, column=col_name,
            ))

    known_col_node_ids: set[str] = {n.id for n in graph.nodes if n.kind == "column"}

    # --- Pass 2: table-level edges ---
    for unique_id, node in all_entries.items():
        if node.get("resource_type", "") not in _WANTED:
            continue
        for dep_id in node.get("depends_on", {}).get("nodes", []):
            if dep_id not in seen_node_ids:
                continue
            graph.add_edge(LineageEdge(
                source=dep_id, target=unique_id,
                kind="derived_from", confidence=1.0,
            ))

    # --- Pass 3: column-level edges from compiled SQL ---
    for unique_id, node in all_entries.items():
        if node.get("resource_type", "") != "model":
            continue
        compiled_sql: str = node.get("compiled_code", "") or node.get("compiled_sql", "")
        if not compiled_sql.strip():
            continue
        if not node.get("columns"):
            continue

        dep_ids = [d for d in node.get("depends_on", {}).get("nodes", []) if d in seen_node_ids]
        if not dep_ids:
            continue

        # Build (unique_id, name) pairs for dependency lookup in sqlglot results.
        dep_nodes = [(dep_id, all_entries[dep_id].get("name", "")) for dep_id in dep_ids]

        edges = _column_edges_from_compiled_sql(
            compiled_sql=compiled_sql,
            dep_nodes=dep_nodes,
            target_unique_id=unique_id,
            known_col_node_ids=known_col_node_ids,
        )
        for edge in edges:
            graph.add_edge(edge)

    return graph
