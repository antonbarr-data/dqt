"""LLM extraction: merge/dedupe, metric flagging, conflict reporting, prose lane.

The LLM is mocked with a fake provider that returns canned JSON per file so the test
is deterministic and offline.
"""
from __future__ import annotations

import json

import pytest

from dqt.ingest import extract

_ORDERS = {
    "datasets": [{
        "schema_name": "sales", "table": "orders", "description": "orders table",
        "primary_key": ["order_id"], "unique_keys": [],
        "columns": [
            {"name": "order_id", "data_type": "STRING", "nullable": False, "description": None,
             "is_time": False, "is_metric": False, "primary_key": True, "unique": False},
            {"name": "order_ts", "data_type": "TIMESTAMP", "nullable": False, "description": None,
             "is_time": True, "is_metric": False, "primary_key": False, "unique": False},
            {"name": "net_amount", "data_type": "NUMERIC", "nullable": True, "description": None,
             "is_time": False, "is_metric": False, "primary_key": False, "unique": False},
        ],
        "metrics": [],
    }],
    "knowledge": [],
}

_REVENUE = {
    "datasets": [{
        "schema_name": "sales", "table": "orders", "description": None,
        "primary_key": [], "unique_keys": [],
        "columns": [
            {"name": "net_amount", "data_type": "DECIMAL", "nullable": True, "description": None,
             "is_time": False, "is_metric": False, "primary_key": False, "unique": False},
        ],
        "metrics": [
            {"name": "total_revenue", "expression": "SUM(net_amount)", "kind": "sum",
             "datatype": "DECIMAL", "description": "revenue", "column_name": "net_amount"},
        ],
    }],
    "knowledge": [],
}

_REFUNDS = {
    "datasets": [],
    "knowledge": [{"title": "Refund policy", "kind": "policy",
                   "body": "revenue recognized after the return window closes"}],
}

_CUSTOMERS = {
    "datasets": [{
        "schema_name": "sales", "table": "customers", "description": "customers",
        "primary_key": ["customer_id"], "unique_keys": [],
        "columns": [
            {"name": "customer_id", "data_type": "STRING", "nullable": False, "description": None,
             "is_time": False, "is_metric": False, "primary_key": True, "unique": False},
        ],
        "metrics": [],
    }],
    "knowledge": [],
}


class _FakeLLM:
    model = "fake"

    def complete(self, messages, *, system=None, model=None, max_tokens=None, temperature=None):
        content = messages[-1]["content"]
        if "revenue.md" in content:
            return json.dumps(_REVENUE)
        if "refunds.md" in content:
            return json.dumps(_REFUNDS)
        if "orders.md" in content:
            return json.dumps(_ORDERS)
        if "sales.yaml" in content:
            return "```json\n" + json.dumps(_CUSTOMERS) + "\n```"  # fenced -> must still parse
        raise AssertionError(f"unexpected unit prompt: {content[:120]}")


def _write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path):
    _write(tmp_path / "okf/tables/orders.md", "---\ntype: BigQuery Table\nresource: acme.sales.orders\n---\n# Schema\n")
    _write(tmp_path / "okf/metrics/revenue.md", "---\ntype: Metric\n---\nSUM(net_amount)\n")
    _write(tmp_path / "okf/policies/refunds.md", "---\ntype: Playbook\n---\npolicy text\n")
    _write(tmp_path / "ossie/sales.yaml", "version: 0.2.0\nsemantic_model:\n  - name: sales\n")
    return tmp_path


def test_extract_merges_and_flags(repo):
    proposal = extract(repo, llm=_FakeLLM())

    by_id = {d.identity: d for d in proposal.datasets}
    assert set(by_id) == {"sales.orders", "sales.customers"}

    orders = by_id["sales.orders"]
    colnames = {c.name for c in orders.columns}
    assert colnames == {"order_id", "order_ts", "net_amount"}
    assert orders.primary_key == ["order_id"]

    # metric merged in from a different file, and its column flagged after merge
    assert [m.name for m in orders.metrics] == ["total_revenue"]
    net = next(c for c in orders.columns if c.name == "net_amount")
    assert net.is_metric is True
    # first-writer-wins on type; conflict recorded
    assert net.data_type == "DECIMAL"
    assert any("net_amount" in c and "type mismatch" in c for c in proposal.conflicts)

    # is_time preserved
    assert next(c for c in orders.columns if c.name == "order_ts").is_time is True


def test_prose_goes_to_knowledge_lane(repo):
    proposal = extract(repo, llm=_FakeLLM())
    assert [k.title for k in proposal.knowledge] == ["Refund policy"]
    assert proposal.knowledge[0].kind == "policy"
    assert proposal.knowledge[0].provenance.format == "okf"
    assert len(proposal.sources_seen) == 4


def test_extract_requires_llm(repo, monkeypatch):
    monkeypatch.delenv("DQT_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="requires an LLM"):
        extract(repo)


def test_invalid_llm_output_recorded_as_conflict(repo):
    class _BadLLM:
        model = "bad"

        def complete(self, messages, **kwargs):
            return "not json at all"

    proposal = extract(repo, llm=_BadLLM())
    assert proposal.datasets == []
    assert len(proposal.conflicts) == 4  # every unit failed extraction
    assert all("extraction failed" in c for c in proposal.conflicts)
