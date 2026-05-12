# packages/dqt/tests/test_alert_deduplication.py
"""Tests for causal-aware alert deduplication."""
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

import dqt
from dqt.algorithms._base import Verdict
from dqt.lineage.dedup import AlertGroup, DeduplicationResult, deduplicate_alerts
from dqt.lineage.models import LineageEdge, LineageGraph, LineageNode
from dqt.store._protocol import Incident


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _incident(check_id: UUID) -> Incident:
    return Incident(
        check_id=check_id,
        run_id=uuid4(),
        detector_slug="completeness",
        severity=Verdict.fail,
        opened_at=_now(),
        score=1.0,
    )


def _check(check_id: UUID, schema: str, table: str, column: str | None = None) -> dqt.Check:
    c = dqt.Check(
        schema_name=schema,
        table_name=table,
        column_name=column,
        detector_slug="completeness",
    )
    object.__setattr__(c, "id", check_id)  # override the Pydantic-generated UUID
    return c


def _graph_with_chain() -> tuple[LineageGraph, list[str]]:
    """Build: source.orders.amount -> mart.revenue.total -> mart.summary.revenue_7d"""
    g = LineageGraph()
    n1 = LineageNode(id="source.orders.amount",     kind="column", label="amount")
    n2 = LineageNode(id="mart.revenue.total",        kind="column", label="total")
    n3 = LineageNode(id="mart.summary.revenue_7d",  kind="column", label="revenue_7d")
    g.add_node(n1); g.add_node(n2); g.add_node(n3)
    g.add_edge(LineageEdge(source="source.orders.amount",    target="mart.revenue.total",        kind="column_lineage"))
    g.add_edge(LineageEdge(source="mart.revenue.total",      target="mart.summary.revenue_7d",   kind="column_lineage"))
    return g, [n1.id, n2.id, n3.id]


def test_single_incident_is_own_root_cause():
    g = LineageGraph()
    nid = "public.orders.amount"
    g.add_node(LineageNode(id=nid, kind="column", label="amount"))
    cid = uuid4()
    inc = _incident(cid)
    chk = _check(cid, "public", "orders", "amount")
    result = deduplicate_alerts([inc], [chk], g)
    assert len(result.groups) == 1
    assert result.groups[0].root_check_id == cid
    assert result.groups[0].downstream_check_ids == []
    assert result.n_suppressed == 0


def test_chain_collapses_to_one_root():
    g, node_ids = _graph_with_chain()
    cid1, cid2, cid3 = uuid4(), uuid4(), uuid4()
    incidents = [_incident(cid1), _incident(cid2), _incident(cid3)]
    checks = [
        _check(cid1, "source", "orders", "amount"),
        _check(cid2, "mart", "revenue", "total"),
        _check(cid3, "mart", "summary", "revenue_7d"),
    ]
    result = deduplicate_alerts(incidents, checks, g)
    assert result.n_root_causes == 1
    assert result.n_suppressed == 2
    group = result.groups[0]
    assert group.root_check_id == cid1
    assert set(group.downstream_check_ids) == {cid2, cid3}


def test_two_independent_failures_produce_two_roots():
    g = LineageGraph()
    g.add_node(LineageNode(id="schema.a.col1", kind="column", label="col1"))
    g.add_node(LineageNode(id="schema.b.col2", kind="column", label="col2"))
    # No edges — completely independent
    cid1, cid2 = uuid4(), uuid4()
    incidents = [_incident(cid1), _incident(cid2)]
    checks = [
        _check(cid1, "schema", "a", "col1"),
        _check(cid2, "schema", "b", "col2"),
    ]
    result = deduplicate_alerts(incidents, checks, g)
    assert result.n_root_causes == 2
    assert result.n_suppressed == 0


def test_unresolved_when_check_not_in_graph():
    g = LineageGraph()  # empty graph — no nodes
    cid = uuid4()
    result = deduplicate_alerts([_incident(cid)], [_check(cid, "public", "orders", "amount")], g)
    assert len(result.unresolved_check_ids) == 1
    assert result.unresolved_check_ids[0] == cid
    assert result.n_root_causes == 0


def test_unresolved_when_check_not_in_checks_list():
    g = LineageGraph()
    cid = uuid4()
    # Pass empty checks list
    result = deduplicate_alerts([_incident(cid)], [], g)
    assert cid in result.unresolved_check_ids


def test_table_level_node_id_when_no_column():
    g = LineageGraph()
    g.add_node(LineageNode(id="public.orders", kind="dataset", label="orders"))
    g.add_node(LineageNode(id="public.revenue", kind="dataset", label="revenue"))
    g.add_edge(LineageEdge(source="public.orders", target="public.revenue", kind="column_lineage"))
    cid1, cid2 = uuid4(), uuid4()
    result = deduplicate_alerts(
        [_incident(cid1), _incident(cid2)],
        [_check(cid1, "public", "orders"), _check(cid2, "public", "revenue")],
        g,
    )
    assert result.n_root_causes == 1
    assert result.groups[0].root_check_id == cid1


def test_exported_from_public_api():
    assert hasattr(dqt, "deduplicate_alerts")
    assert hasattr(dqt, "AlertGroup")
    assert hasattr(dqt, "DeduplicationResult")


def test_dedup_result_properties():
    result = DeduplicationResult(groups=[
        AlertGroup(root_check_id=uuid4(), root_node_id="a", downstream_check_ids=[uuid4(), uuid4()]),
        AlertGroup(root_check_id=uuid4(), root_node_id="b"),
    ])
    assert result.n_root_causes == 2
    assert result.n_suppressed == 2
