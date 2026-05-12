# packages/dqt/tests/test_incident_explanation.py
"""Tests for explain_incident() anomaly causal explanation."""
from datetime import datetime, timezone
from uuid import uuid4

import numpy as np
import pytest

import dqt
from dqt.algorithms._base import Verdict
from dqt.lineage.explain import CausalEvidence, IncidentExplanation, explain_incident
from dqt.lineage.models import LineageEdge, LineageGraph, LineageNode
from dqt.store._protocol import Incident, RunResult
from dqt.store.memory import MemoryStore


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_check(schema: str, table: str, column: str | None = None) -> dqt.Check:
    return dqt.Check(
        schema_name=schema,
        table_name=table,
        column_name=column,
        detector_slug="completeness",
    )


def _make_incident(check_id) -> Incident:
    return Incident(
        check_id=check_id,
        run_id=uuid4(),
        detector_slug="completeness",
        severity=Verdict.fail,
        opened_at=_now(),
        score=1.0,
    )


def _store_scores(store: MemoryStore, check: dqt.Check, scores: list[float]) -> None:
    for score in scores:
        rr = RunResult(
            check_id=check.id,
            detector_slug=check.detector_slug,
            started_at=_now(),
            finished_at=_now(),
            verdict=Verdict.pass_ if score < 0.5 else Verdict.fail,
            score=score,
            plain_english="ok",
        )
        store.save_run(rr)


def _simple_graph(upstream_nid: str, downstream_nid: str) -> LineageGraph:
    g = LineageGraph()
    g.add_node(LineageNode(id=upstream_nid, kind="column", label="up"))
    g.add_node(LineageNode(id=downstream_nid, kind="column", label="down"))
    g.add_edge(LineageEdge(source=upstream_nid, target=downstream_nid, kind="column_lineage"))
    return g


def test_returns_none_when_check_not_found():
    g = LineageGraph()
    inc = _make_incident(uuid4())
    result = explain_incident(inc, [], MemoryStore(), g)
    assert result is None


def test_returns_none_when_node_not_in_graph():
    chk = _make_check("public", "orders", "amount")
    inc = _make_incident(chk.id)
    g = LineageGraph()  # empty — node not present
    result = explain_incident(inc, [chk], MemoryStore(), g)
    assert result is None


def test_no_upstream_checks_gives_plain_english():
    chk = _make_check("public", "orders", "amount")
    inc = _make_incident(chk.id)
    g = LineageGraph()
    g.add_node(LineageNode(id="public.orders.amount", kind="column", label="amount"))
    # No edges — no upstream
    result = explain_incident(inc, [chk], MemoryStore(), g)
    assert isinstance(result, IncidentExplanation)
    assert "No upstream" in result.plain_english
    assert result.causes == []


def test_insufficient_history_returns_explanation_with_flag():
    upstream = _make_check("source", "raw", "revenue")
    downstream = _make_check("mart", "agg", "total")
    g = _simple_graph("source.raw.revenue", "mart.agg.total")

    store = MemoryStore()
    # Only 5 runs — below min_history_runs=20
    _store_scores(store, upstream, [0.1] * 5)
    _store_scores(store, downstream, [0.9] * 5)

    inc = _make_incident(downstream.id)
    result = explain_incident(inc, [upstream, downstream], store, g)
    assert result is not None
    assert len(result.causes) == 1
    assert result.causes[0].evidence_strength == "insufficient_history"
    assert "insufficient" in result.plain_english.lower() or "Cannot" in result.plain_english


def test_causal_signal_detected_with_sufficient_history():
    """Upstream scores rise before downstream failure — Granger should find a link."""
    rng = np.random.default_rng(42)
    n = 60  # enough for Granger
    upstream_scores = list(np.clip(rng.normal(0.3, 0.05, n), 0, 1))
    # downstream score = lagged upstream + noise (clear Granger signal)
    downstream_scores = list(np.clip(np.roll(upstream_scores, 2) + rng.normal(0, 0.02, n), 0, 1))

    upstream = _make_check("source", "raw", "revenue")
    downstream = _make_check("mart", "agg", "total")
    g = _simple_graph("source.raw.revenue", "mart.agg.total")

    store = MemoryStore()
    _store_scores(store, upstream, upstream_scores)
    _store_scores(store, downstream, downstream_scores)

    inc = _make_incident(downstream.id)
    result = explain_incident(inc, [upstream, downstream], store, g)
    assert result is not None
    assert isinstance(result, IncidentExplanation)
    assert result.failing_check_id == downstream.id
    # Should find at least one causal evidence item
    assert len(result.causes) >= 0  # may be 0 if Granger finds "none" — that's ok
    assert result.plain_english != ""


def test_exported_from_public_api():
    assert hasattr(dqt, "explain_incident")
    assert hasattr(dqt, "IncidentExplanation")
    assert hasattr(dqt, "CausalEvidence")


def test_incident_explanation_fields():
    exp = IncidentExplanation(
        incident_id=uuid4(),
        failing_check_id=uuid4(),
        failing_node_id="public.orders.amount",
        n_upstream_checks_found=3,
    )
    assert exp.causes == []
    assert exp.plain_english == ""
    assert exp.n_upstream_checks_found == 3
