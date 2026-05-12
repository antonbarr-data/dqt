from fastapi.testclient import TestClient
from datetime import datetime
from dqt.store.memory import MemoryStore
from dqt.store._protocol import CausalityReport
from dqt.dashboard.app import build_app


def _client_with_edge():
    store = MemoryStore()
    store.save_causality_report(CausalityReport(
        dataset_name="metrics", ran_at=datetime.now(),
        n_pairs_tested=1, n_significant=1,
        edges=[{
            "cause": "ad_spend", "effect": "revenue",
            "evidence_strength": "strong", "selected_lag": 1,
            "f_statistic": 20.0, "edge_id": "aaaaaaaa-0000-0000-0000-000000000001",
        }],
    ))
    return TestClient(build_app(store)), store


def test_review_accept_redirects():
    client, store = _client_with_edge()
    resp = client.post("/causality/review", data={
        "edge_id": "aaaaaaaa-0000-0000-0000-000000000001",
        "cause": "ad_spend", "effect": "revenue",
        "decision": "accept", "reviewer": "test", "reason": "makes sense",
    }, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/causality"


def test_review_reject_saves_to_store():
    client, store = _client_with_edge()
    client.post("/causality/review", data={
        "edge_id": "aaaaaaaa-0000-0000-0000-000000000001",
        "cause": "ad_spend", "effect": "revenue",
        "decision": "reject", "reviewer": "test", "reason": "",
    })
    from uuid import UUID
    reviews = store.list_causal_reviews(UUID("aaaaaaaa-0000-0000-0000-000000000001"))
    assert len(reviews) == 1
    assert reviews[0].decision == "reject"
