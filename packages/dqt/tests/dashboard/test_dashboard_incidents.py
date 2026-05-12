from fastapi.testclient import TestClient
from datetime import datetime, timezone
from uuid import uuid4
from dqt.store.memory import MemoryStore
from dqt.store._protocol import Incident, RunResult
from dqt.algorithms._base import Verdict
from dqt.dashboard.app import build_app


def _make_client():
    store = MemoryStore()
    check_id = uuid4()
    run_id = uuid4()
    store.save_run(RunResult(
        check_id=check_id, run_id=run_id, detector_slug="null_fraction",
        started_at=datetime.now(timezone.utc), finished_at=datetime.now(timezone.utc),
        verdict=Verdict.fail, score=0.15, plain_english="15% null",
        details={"n_null": 15, "n_total": 100},
    ))
    store.save_incident(Incident(
        check_id=check_id, run_id=run_id, detector_slug="null_fraction",
        severity=Verdict.fail, opened_at=datetime.now(timezone.utc), score=0.15,
    ))
    return TestClient(build_app(store)), str(check_id)


def test_incidents_list_200():
    client, _ = _make_client()
    resp = client.get("/incidents")
    assert resp.status_code == 200
    assert "null_fraction" in resp.text


def test_incident_detail_200():
    client, check_id = _make_client()
    resp = client.get(f"/incidents/{check_id}")
    assert resp.status_code == 200
    assert "null_fraction" in resp.text


def test_incident_detail_unknown_id_200():
    client, _ = _make_client()
    resp = client.get("/incidents/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 200  # graceful empty page, not 500
