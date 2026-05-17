from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field


@dataclass
class LineageNode:
    id: str                      # e.g. "marketing_campaigns.spend_usd"
    kind: str                    # "source" | "dataset" | "column" | "metric"
    label: str                   # display name
    dataset: str = ""
    column: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class LineageEdge:
    source: str                  # node id
    target: str                  # node id
    kind: str                    # "column_lineage" | "causality" | "derived_from" | "aggregates"
    lag_weeks: int = 0
    confidence: float = 1.0
    description: str = ""


@dataclass
class LineageGraph:
    nodes: list[LineageNode] = field(default_factory=list)
    edges: list[LineageEdge] = field(default_factory=list)

    def add_node(self, node: LineageNode) -> None:
        self.nodes.append(node)

    def add_edge(self, edge: LineageEdge) -> None:
        self.edges.append(edge)

    def downstream(self, node_id: str) -> list[LineageNode]:
        """Direct (one-hop) downstream neighbours."""
        target_ids = {e.target for e in self.edges if e.source == node_id}
        return [n for n in self.nodes if n.id in target_ids]

    def upstream(self, node_id: str) -> list[LineageNode]:
        """Direct (one-hop) upstream neighbours."""
        source_ids = {e.source for e in self.edges if e.target == node_id}
        return [n for n in self.nodes if n.id in source_ids]

    def all_downstream(self, node_id: str) -> list[LineageNode]:
        """All transitive downstream nodes (BFS, excluding the start node)."""
        node_index = {n.id: n for n in self.nodes}
        visited: set[str] = set()
        queue: deque[str] = deque([node_id])
        while queue:
            current = queue.popleft()
            for e in self.edges:
                if e.source == current and e.target not in visited and e.target != node_id:
                    visited.add(e.target)
                    queue.append(e.target)
        return [node_index[nid] for nid in visited if nid in node_index]

    def all_upstream(self, node_id: str) -> list[LineageNode]:
        """All transitive upstream nodes (BFS, excluding the start node)."""
        node_index = {n.id: n for n in self.nodes}
        visited: set[str] = set()
        queue: deque[str] = deque([node_id])
        while queue:
            current = queue.popleft()
            for e in self.edges:
                if e.target == current and e.source not in visited and e.source != node_id:
                    visited.add(e.source)
                    queue.append(e.source)
        return [node_index[nid] for nid in visited if nid in node_index]

    def subgraph(self, root: str, direction: str = "both", depth: int = 3) -> "LineageGraph":
        """Return a new LineageGraph containing nodes within *depth* hops of *root*.

        direction: "downstream" | "upstream" | "both"
        """
        node_index = {n.id: n for n in self.nodes}
        included: set[str] = {root}
        queue: deque[tuple[str, int]] = deque([(root, 0)])
        while queue:
            current, dist = queue.popleft()
            if dist >= depth:
                continue
            for e in self.edges:
                if direction in ("downstream", "both") and e.source == current and e.target not in included:
                    included.add(e.target)
                    queue.append((e.target, dist + 1))
                if direction in ("upstream", "both") and e.target == current and e.source not in included:
                    included.add(e.source)
                    queue.append((e.source, dist + 1))
        sg = LineageGraph()
        for nid in included:
            if nid in node_index:
                sg.add_node(node_index[nid])
        for e in self.edges:
            if e.source in included and e.target in included:
                sg.add_edge(e)
        return sg

    def shortest_path(self, source: str, target: str) -> list[str] | None:
        """BFS shortest path from *source* to *target* following directed edges.

        Returns the node-id list [source, ..., target] or None if no path exists.
        """
        if source == target:
            return [source]
        adjacency: dict[str, list[str]] = {}
        for e in self.edges:
            adjacency.setdefault(e.source, []).append(e.target)
        visited: set[str] = {source}
        queue: deque[list[str]] = deque([[source]])
        while queue:
            path = queue.popleft()
            node = path[-1]
            for neighbour in adjacency.get(node, []):
                if neighbour == target:
                    return path + [neighbour]
                if neighbour not in visited:
                    visited.add(neighbour)
                    queue.append(path + [neighbour])
        return None
