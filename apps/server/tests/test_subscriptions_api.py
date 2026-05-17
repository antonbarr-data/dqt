from fastapi.testclient import TestClient
from dqt_server.main import app

client = TestClient(app)


def test_create_subscription_returns_200():
    resp = client.post("/api/v1/subscriptions", json={
        "user_id": "alice",
        "metric_fqns": ["gigler.default.orders.quality"],
        "cadence": "daily",
        "delivery_channels": ["email"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "alice"
    assert "gigler.default.orders.quality" in data["metric_fqns"]
    assert "id" in data


def test_list_subscriptions_returns_created_items():
    client.post("/api/v1/subscriptions", json={
        "user_id": "listtest",
        "metric_fqns": ["m1"],
        "cadence": "weekly",
        "delivery_channels": ["slack"],
    })
    resp = client.get("/api/v1/subscriptions?user_id=listtest")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(s["user_id"] == "listtest" for s in data)


def test_update_subscription_changes_cadence():
    create_resp = client.post("/api/v1/subscriptions", json={
        "user_id": "updatetest",
        "metric_fqns": ["m1"],
        "cadence": "daily",
        "delivery_channels": ["email"],
    })
    sub_id = create_resp.json()["id"]
    resp = client.put(f"/api/v1/subscriptions/{sub_id}", json={"cadence": "weekly"})
    assert resp.status_code == 200
    assert resp.json()["cadence"] == "weekly"


def test_delete_subscription_returns_deleted_true():
    create_resp = client.post("/api/v1/subscriptions", json={
        "user_id": "deletetest",
        "metric_fqns": ["m1"],
        "cadence": "daily",
        "delivery_channels": ["email"],
    })
    sub_id = create_resp.json()["id"]
    resp = client.delete(f"/api/v1/subscriptions/{sub_id}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


def test_delete_nonexistent_returns_404():
    resp = client.delete("/api/v1/subscriptions/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_update_nonexistent_returns_404():
    resp = client.put("/api/v1/subscriptions/00000000-0000-0000-0000-000000000000", json={"cadence": "weekly"})
    assert resp.status_code == 404


def test_preview_subscription_returns_plain_text_and_html():
    create_resp = client.post("/api/v1/subscriptions", json={
        "user_id": "previewtest",
        "metric_fqns": ["gigler.default.orders.quality"],
        "cadence": "daily",
        "delivery_channels": ["email"],
    })
    sub_id = create_resp.json()["id"]
    resp = client.get(f"/api/v1/subscriptions/{sub_id}/preview")
    assert resp.status_code == 200
    data = resp.json()
    assert "plain_text" in data
    assert "html" in data
    assert "Daily Digest" in data["plain_text"]
