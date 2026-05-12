# packages/dqt/tests/dashboard/test_dashboard.py
from datetime import datetime, timezone
from uuid import uuid4

import pytest


@pytest.mark.unit
def test_dashboard_create_app_importable():
    """create_app must be importable and return a FastAPI app when deps are present."""
    pytest.importorskip("fastapi", reason="dqtlib[dashboard] not installed")
    from dqt.dashboard import create_app
    from dqt.store.memory import MemoryStore

    store = MemoryStore()
    app = create_app(store=store)
    assert app is not None
    assert hasattr(app, "routes")


@pytest.mark.unit
def test_dashboard_index_endpoint():
    """GET / must return 200 with HTML containing 'dqt'."""
    pytest.importorskip("fastapi", reason="dqtlib[dashboard] not installed")
    from fastapi.testclient import TestClient

    from dqt.dashboard import create_app
    from dqt.store.memory import MemoryStore

    store = MemoryStore()
    app = create_app(store=store)
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "dqt" in response.text.lower()


@pytest.mark.unit
def test_dashboard_health_endpoint():
    """GET /health must return 200 with status ok."""
    pytest.importorskip("fastapi", reason="dqtlib[dashboard] not installed")
    from fastapi.testclient import TestClient

    from dqt.dashboard import create_app
    from dqt.store.memory import MemoryStore

    store = MemoryStore()
    app = create_app(store=store)
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.unit
def test_dashboard_index_shows_saved_runs():
    """GET / renders a saved run's check_id in the page."""
    pytest.importorskip("fastapi", reason="dqtlib[dashboard] not installed")
    from fastapi.testclient import TestClient

    from dqt.algorithms._base import Verdict
    from dqt.dashboard import create_app
    from dqt.store._protocol import RunResult
    from dqt.store.memory import MemoryStore

    now = datetime.now(tz=timezone.utc)
    check_id = uuid4()
    run = RunResult(
        check_id=check_id,
        detector_slug="completeness",
        started_at=now,
        finished_at=now,
        verdict=Verdict.pass_,
        score=0.99,
        plain_english="All good",
    )
    store = MemoryStore()
    store.save_run(run)
    app = create_app(store=store)
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert str(check_id) in response.text


@pytest.mark.unit
def test_dashboard_check_detail_endpoint():
    """GET /checks/{id} renders run history for a known check."""
    pytest.importorskip("fastapi", reason="dqtlib[dashboard] not installed")
    from fastapi.testclient import TestClient

    from dqt.algorithms._base import Verdict
    from dqt.dashboard import create_app
    from dqt.store._protocol import RunResult
    from dqt.store.memory import MemoryStore

    now = datetime.now(tz=timezone.utc)
    check_id = uuid4()
    run = RunResult(
        check_id=check_id,
        detector_slug="completeness",
        started_at=now,
        finished_at=now,
        verdict=Verdict.warn,
        score=0.87,
        plain_english="Some nulls detected",
    )
    store = MemoryStore()
    store.save_run(run)
    app = create_app(store=store)
    client = TestClient(app)
    response = client.get(f"/checks/{check_id}")
    assert response.status_code == 200
    assert "Some nulls detected" in response.text
