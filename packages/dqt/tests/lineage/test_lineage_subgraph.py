# packages/dqt/tests/lineage/test_lineage_subgraph.py
from __future__ import annotations
import pytest
from dqt.lineage import LineageEdge, LineageGraph, LineageNode


def _g() -> LineageGraph:
    """
    A -> B -> D
    A -> C -> D
    C -> E
    """
    g = LineageGraph()
    for nid in ["A", "B", "C", "D", "E"]:
        g.add_node(LineageNode(id=nid, kind="metric", label=nid))
    g.add_edge(LineageEdge(source="A", target="B", kind="column_lineage"))
    g.add_edge(LineageEdge(source="A", target="C", kind="column_lineage"))
    g.add_edge(LineageEdge(source="B", target="D", kind="column_lineage"))
    g.add_edge(LineageEdge(source="C", target="D", kind="column_lineage"))
    g.add_edge(LineageEdge(source="C", target="E", kind="column_lineage"))
    return g


def test_subgraph_depth_1():
    g = _g()
    sg = g.subgraph("A", direction="downstream", depth=1)
    node_ids = {n.id for n in sg.nodes}
    assert node_ids == {"A", "B", "C"}
    assert len(sg.edges) == 2


def test_subgraph_depth_2():
    g = _g()
    sg = g.subgraph("A", direction="downstream", depth=2)
    node_ids = {n.id for n in sg.nodes}
    assert node_ids == {"A", "B", "C", "D", "E"}


def test_subgraph_upstream():
    g = _g()
    sg = g.subgraph("D", direction="upstream", depth=2)
    node_ids = {n.id for n in sg.nodes}
    assert "A" in node_ids
    assert "B" in node_ids
    assert "C" in node_ids
    assert "D" in node_ids


def test_subgraph_both():
    g = _g()
    sg = g.subgraph("C", direction="both", depth=1)
    node_ids = {n.id for n in sg.nodes}
    assert "A" in node_ids  # upstream
    assert "D" in node_ids  # downstream
    assert "E" in node_ids  # downstream


def test_shortest_path_exists():
    g = _g()
    path = g.shortest_path("A", "E")
    assert path is not None
    assert path[0] == "A"
    assert path[-1] == "E"
    assert len(path) == 3  # A -> C -> E


def test_shortest_path_none():
    g = _g()
    path = g.shortest_path("E", "A")  # no path upstream in directed graph
    assert path is None


def test_shortest_path_same_node():
    g = _g()
    path = g.shortest_path("A", "A")
    assert path == ["A"]
