# packages/dqt/tests/lineage/test_lineage_graph_property.py
"""Property-based tests for LineageGraph (C.11)."""
from __future__ import annotations
from collections import deque
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from dqt.lineage import LineageEdge, LineageGraph, LineageNode


def _make_graph(nodes: list[str], edges: list[tuple[str, str]]) -> LineageGraph:
    """Build a LineageGraph from node-id strings and (source, target) pairs."""
    g = LineageGraph()
    for nid in nodes:
        g.add_node(LineageNode(id=nid, kind="dataset", label=nid))
    for src, tgt in edges:
        g.add_edge(LineageEdge(source=src, target=tgt, kind="column_lineage"))
    return g


def _brute_force_upstream(edges: list[tuple[str, str]], node: str) -> set[str]:
    """Reference BFS for upstream reachability (excluding the start node)."""
    upstream: dict[str, list[str]] = {}
    for src, dst in edges:
        upstream.setdefault(dst, []).append(src)
    visited: set[str] = set()
    queue: deque[str] = deque([node])
    while queue:
        n = queue.popleft()
        for parent in upstream.get(n, []):
            if parent not in visited and parent != node:
                visited.add(parent)
                queue.append(parent)
    return visited


def _brute_force_downstream(edges: list[tuple[str, str]], node: str) -> set[str]:
    """Reference BFS for downstream reachability (excluding the start node)."""
    downstream: dict[str, list[str]] = {}
    for src, dst in edges:
        downstream.setdefault(src, []).append(dst)
    visited: set[str] = set()
    queue: deque[str] = deque([node])
    while queue:
        n = queue.popleft()
        for child in downstream.get(n, []):
            if child not in visited and child != node:
                visited.add(child)
                queue.append(child)
    return visited


@st.composite
def dag_and_node(draw):
    """Random DAG (only forward edges to guarantee acyclicity) + target node."""
    n_nodes = draw(st.integers(min_value=2, max_value=10))
    nodes = [f"n{i}" for i in range(n_nodes)]
    edges = []
    for i in range(n_nodes):
        for j in range(i + 1, n_nodes):
            if draw(st.booleans()):
                edges.append((nodes[i], nodes[j]))
    target = draw(st.sampled_from(nodes))
    return nodes, edges, target


@given(dag_and_node())
@settings(max_examples=100)
def test_all_upstream_matches_bfs(dag_and_node_val):
    nodes, edges, target = dag_and_node_val
    g = _make_graph(nodes, edges)
    result = {n.id for n in g.all_upstream(target)}
    expected = _brute_force_upstream(edges, target)
    assert result == expected


@given(dag_and_node())
@settings(max_examples=100)
def test_all_downstream_matches_bfs(dag_and_node_val):
    nodes, edges, target = dag_and_node_val
    g = _make_graph(nodes, edges)
    result = {n.id for n in g.all_downstream(target)}
    expected = _brute_force_downstream(edges, target)
    assert result == expected


@given(dag_and_node())
@settings(max_examples=100)
def test_node_not_in_own_upstream_or_downstream(dag_and_node_val):
    nodes, edges, target = dag_and_node_val
    g = _make_graph(nodes, edges)
    upstream_ids = {n.id for n in g.all_upstream(target)}
    downstream_ids = {n.id for n in g.all_downstream(target)}
    assert target not in upstream_ids
    assert target not in downstream_ids
