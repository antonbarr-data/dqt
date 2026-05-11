"""dbt manifest.json ingestion for column-level lineage.
Ref: https://docs.getdbt.com/reference/artifacts/manifest-json (format v10+)
"""
from __future__ import annotations

import json
from pathlib import Path

from dqt.lineage.models import LineageEdge, LineageGraph, LineageNode


def from_dbt_manifest(manifest_path: str | Path) -> LineageGraph:
    """Parse a dbt manifest.json and return a LineageGraph.

    Example::

        graph = from_dbt_manifest("target/manifest.json")
        print(len(graph.nodes), "datasets")
        print(len(graph.edges), "lineage edges")
    """
    path = Path(manifest_path)
    manifest: dict = json.loads(path.read_text(encoding="utf-8"))

    graph = LineageGraph()
    seen_node_ids: set[str] = set()

    # dbt manifest v10+: top-level "nodes" contains models and tests;
    # "sources" contains source nodes.  Merge both for uniform treatment.
    all_entries: dict[str, dict] = {}
    all_entries.update(manifest.get("nodes", {}))
    all_entries.update(manifest.get("sources", {}))

    _WANTED = {"model", "source"}

    for unique_id, node in all_entries.items():
        resource_type = node.get("resource_type", "")
        if resource_type not in _WANTED:
            continue

        name = node.get("name", unique_id)
        graph.add_node(
            LineageNode(
                id=unique_id,
                kind="dataset",
                label=name,
                dataset=name,
            )
        )
        seen_node_ids.add(unique_id)

    # Build edges from depends_on.nodes
    for unique_id, node in all_entries.items():
        if node.get("resource_type", "") not in _WANTED:
            continue
        depends_on: list[str] = node.get("depends_on", {}).get("nodes", [])
        for dep_id in depends_on:
            # Only link nodes we already ingested; deps may include tests etc.
            if dep_id not in seen_node_ids:
                continue
            graph.add_edge(
                LineageEdge(
                    source=dep_id,
                    target=unique_id,
                    kind="derived_from",
                    confidence=1.0,
                )
            )

    return graph
