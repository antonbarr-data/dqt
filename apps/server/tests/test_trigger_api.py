from fastapi.testclient import TestClient
from dqt_server.main import app

client = TestClient(app)


def test_trigger_threshold_dry_run():
    resp = client.post("/api/v1/trigger", json={"mode": "threshold", "dry_run": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "threshold"
    assert data["dry_run"] is True
    assert "triggered" in data
    assert "skipped" in data


def test_trigger_daily_dry_run_returns_digest():
    resp = client.post("/api/v1/trigger", json={"mode": "daily", "dry_run": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["cadence"] == "daily"
    assert "plain_text" in data
    assert "Daily Digest" in data["plain_text"]


def test_trigger_weekly_dry_run_returns_digest():
    resp = client.post("/api/v1/trigger", json={"mode": "weekly", "dry_run": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["cadence"] == "weekly"
    assert "plain_text" in data
    assert "Weekly Digest" in data["plain_text"]


def test_digest_history_grows_with_each_trigger():
    client.post("/api/v1/trigger", json={"mode": "daily", "dry_run": True})
    resp = client.get("/api/v1/trigger/history")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "cadence" in data[0]
    assert "generated_at" in data[0]
