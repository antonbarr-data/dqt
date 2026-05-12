# packages/dqt/tests/dashboard/test_dashboard_lineage.py
import pytest


@pytest.mark.unit
def test_lineage_route_no_graph():
    """GET /lineage without a graph returns 200 with 'lineage' in the page."""
    pytest.importorskip("fastapi", reason="dqtlib[dashboard] not installed")
    from fastapi.testclient import TestClient

    from dqt.dashboard.app import build_app
    from dqt.store.memory import MemoryStore

    client = TestClient(build_app(MemoryStore()))
    resp = client.get("/lineage")
    assert resp.status_code == 200
    assert "lineage" in resp.text.lower()


@pytest.mark.unit
def test_lineage_route_with_graph():
    """GET /lineage with a graph renders node labels in the page."""
    pytest.importorskip("fastapi", reason="dqtlib[dashboard] not installed")
    from fastapi.testclient import TestClient

    from dqt.dashboard.app import build_app
    from dqt.lineage.models import LineageEdge, LineageGraph, LineageNode
    from dqt.store.memory import MemoryStore

    graph = LineageGraph()
    graph.add_node(LineageNode(
        id="orders.customer_id",
        kind="column",
        label="customer_id",
        dataset="orders",
        column="customer_id",
    ))
    graph.add_node(LineageNode(
        id="fct_orders.customer_id",
        kind="column",
        label="customer_id",
        dataset="fct_orders",
        column="customer_id",
    ))
    graph.add_edge(LineageEdge(
        source="orders.customer_id",
        target="fct_orders.customer_id",
        kind="column_lineage",
    ))

    client = TestClient(build_app(MemoryStore(), lineage_graph=graph))
    resp = client.get("/lineage")
    assert resp.status_code == 200
    assert "customer_id" in resp.text


@pytest.mark.unit
def test_lineage_route_create_app():
    """create_app forwards lineage_graph= to build_app."""
    pytest.importorskip("fastapi", reason="dqtlib[dashboard] not installed")
    from fastapi.testclient import TestClient

    from dqt.dashboard import create_app
    from dqt.lineage.models import LineageEdge, LineageGraph, LineageNode
    from dqt.store.memory import MemoryStore

    graph = LineageGraph()
    graph.add_node(LineageNode(
        id="sales.revenue",
        kind="column",
        label="revenue",
        dataset="sales",
        column="revenue",
    ))
    graph.add_edge(LineageEdge(
        source="sales.revenue",
        target="sales.revenue",
        kind="derived_from",
    ))

    client = TestClient(create_app(store=MemoryStore(), lineage_graph=graph))
    resp = client.get("/lineage")
    assert resp.status_code == 200
    assert "revenue" in resp.text
