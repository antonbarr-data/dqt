import os
from fastapi.testclient import TestClient
from dqt.store.memory import MemoryStore
from dqt.dashboard.app import build_app


def test_no_token_set_allows_all(monkeypatch):
    monkeypatch.delenv("DQT_DASHBOARD_TOKEN", raising=False)
    client = TestClient(build_app(MemoryStore()))
    assert client.get("/").status_code == 200


def test_correct_bearer_token_allows_access(monkeypatch):
    monkeypatch.setenv("DQT_DASHBOARD_TOKEN", "secret123")
    client = TestClient(build_app(MemoryStore()))
    assert client.get("/", headers={"Authorization": "Bearer secret123"}).status_code == 200


def test_wrong_token_returns_401(monkeypatch):
    monkeypatch.setenv("DQT_DASHBOARD_TOKEN", "secret123")
    client = TestClient(build_app(MemoryStore()))
    assert client.get("/", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_missing_auth_header_returns_401(monkeypatch):
    monkeypatch.setenv("DQT_DASHBOARD_TOKEN", "secret123")
    client = TestClient(build_app(MemoryStore()))
    assert client.get("/").status_code == 401


def test_health_bypasses_auth(monkeypatch):
    monkeypatch.setenv("DQT_DASHBOARD_TOKEN", "secret123")
    client = TestClient(build_app(MemoryStore()))
    assert client.get("/health").status_code == 200
