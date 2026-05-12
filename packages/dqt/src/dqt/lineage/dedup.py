# packages/dqt/src/dqt/lineage/dedup.py
"""Causal-aware alert deduplication.

Given a set of concurrent open incidents and the lineage graph, collapses
downstream consequences into a single root-cause alert group. Prevents alert
storms where one upstream failure triggers N downstream failures.

Algorithm:
1. Map each incident to a lineage node via (schema.table.column or schema.table).
2. Build a "failing nodes" set from all resolved incidents.
3. For each failing node, walk all_upstream() — if any upstream node is also
   failing, this node is downstream and belongs to that upstream's group.
4. Nodes with no failing upstream are root causes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from dqt.lineage.models import LineageGraph


@dataclass
class AlertGroup:
    """One root cause and all its downstream incidents in the same failure chain."""
    root_check_id: UUID
    root_node_id: str
    downstream_check_ids: list[UUID] = field(default_factory=list)
    downstream_node_ids: list[str] = field(default_factory=list)


@dataclass
class DeduplicationResult:
    """Result of deduplicate_alerts()."""
    groups: list[AlertGroup]
    # Incidents whose checks could not be resolved to a lineage node
    unresolved_check_ids: list[UUID] = field(default_factory=list)

    @property
    def n_root_causes(self) -> int:
        return len(self.groups)

    @property
    def n_suppressed(self) -> int:
        return sum(len(g.downstream_check_ids) for g in self.groups)


def _node_id_for_check(schema: str, table: str, column: str | None) -> str:
    if column:
        return f"{schema}.{table}.{column}"
    return f"{schema}.{table}"


def deduplicate_alerts(
    incidents: list,
    checks: list,
    graph: LineageGraph,
) -> DeduplicationResult:
    """Collapse chained alert failures into root-cause groups.

    Args:
        incidents: list of Incident objects (must have check_id attribute).
        checks: list of Check objects (must have id, schema_name, table_name,
                column_name attributes). Only checks referenced by incidents
                need to be included.
        graph: LineageGraph with nodes and edges covering the failing checks.

    Returns:
        DeduplicationResult with alert groups and unresolved check IDs.

    Example:
        result = deduplicate_alerts(open_incidents, checks, lineage_graph)
        for group in result.groups:
            notify(group.root_check_id)  # send one alert per group
            for cid in group.downstream_check_ids:
                suppress(cid)           # skip the downstream noise
    """
    check_map = {c.id: c for c in checks}
    node_index = {n.id: n for n in graph.nodes}

    # Map incident check_id → lineage node_id
    check_to_node: dict[UUID, str] = {}
    unresolved: list[UUID] = []
    for inc in incidents:
        check = check_map.get(inc.check_id)
        if check is None:
            unresolved.append(inc.check_id)
            continue
        nid = _node_id_for_check(check.schema_name, check.table_name, check.column_name)
        if nid in node_index:
            check_to_node[inc.check_id] = nid
        else:
            unresolved.append(inc.check_id)

    failing_nodes: set[str] = set(check_to_node.values())
    node_to_check: dict[str, UUID] = {v: k for k, v in check_to_node.items()}

    # For each failing node, find its most-upstream failing ancestor
    def _root_failing_ancestor(node_id: str) -> str | None:
        """Return the farthest-upstream failing node, or None if this is itself the root."""
        upstream_all = {n.id for n in graph.all_upstream(node_id)}
        failing_upstream = upstream_all & failing_nodes
        if not failing_upstream:
            return None
        # Walk from node_id upward; pick the one with no failing upstream itself
        for candidate in failing_upstream:
            candidate_upstream = {n.id for n in graph.all_upstream(candidate)}
            if not candidate_upstream & failing_nodes:
                return candidate
        # Fallback: return any one of the failing upstreams
        return next(iter(failing_upstream))

    # Build groups
    groups_by_root: dict[str, AlertGroup] = {}
    downstream_nodes: set[str] = set()

    for check_id, node_id in check_to_node.items():
        root_node = _root_failing_ancestor(node_id)
        if root_node is None:
            # This node is itself a root cause
            if node_id not in groups_by_root:
                groups_by_root[node_id] = AlertGroup(
                    root_check_id=check_id,
                    root_node_id=node_id,
                )
        else:
            downstream_nodes.add(node_id)
            if root_node not in groups_by_root:
                root_check_id = node_to_check[root_node]
                groups_by_root[root_node] = AlertGroup(
                    root_check_id=root_check_id,
                    root_node_id=root_node,
                )
            group = groups_by_root[root_node]
            if check_id not in group.downstream_check_ids:
                group.downstream_check_ids.append(check_id)
                group.downstream_node_ids.append(node_id)

    # Ensure every root-cause node has a group (even if no downstreams were found)
    for check_id, node_id in check_to_node.items():
        if node_id not in downstream_nodes and node_id not in groups_by_root:
            groups_by_root[node_id] = AlertGroup(
                root_check_id=check_id,
                root_node_id=node_id,
            )

    return DeduplicationResult(
        groups=list(groups_by_root.values()),
        unresolved_check_ids=unresolved,
    )
