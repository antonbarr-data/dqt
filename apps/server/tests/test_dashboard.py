"""Tests for the HTMX dashboard — no auth, no DB required."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from dqt.algorithms._base import DetectorResult, Verdict
from dqt_server.dashboard import STATE
from dqt_server.main import app


@pytest.fixture(autouse=True)
def _clear_state():
    """Reset singleton state between tests."""
    STATE._runs.clear()
    yield
    STATE._runs.clear()


client = TestClient(app)


def test_dashboard_index_200() -> None:
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "dqt dashboard" in resp.text


def test_dashboard_check_unknown_id_200() -> None:
    """Unknown check_id should return 200 with an empty-state message, not 404."""
    resp = client.get("/dashboard/checks/unknown-id")
    assert resp.status_code == 200
    assert "unknown-id" in resp.text


def test_dashboard_index_shows_check_row() -> None:
    STATE.add_result(
        "check-abc",
        DetectorResult(
            score=0.42,
            verdict=Verdict.warn,
            plain_english="Score is elevated.",
            details={"p_value": 0.042},
        ),
        detector_slug="ks",
    )
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "check-abc" in resp.text
    assert "warn" in resp.text


def test_dashboard_check_detail_shows_score() -> None:
    STATE.add_result(
        "check-xyz",
        DetectorResult(
            score=0.95,
            verdict=Verdict.pass_,
            plain_english="Distribution looks stable.",
            details={"stat": 0.95, "p_value": 0.3},
            failing_filter_sql="score > 0.9",
        ),
        detector_slug="zscore",
    )
    resp = client.get("/dashboard/checks/check-xyz")
    assert resp.status_code == 200
    assert "0.9500" in resp.text
    assert "Distribution looks stable." in resp.text
    assert "score &gt; 0.9" in resp.text or "score > 0.9" in resp.text


def test_dashboard_run_post_htmx_partial() -> None:
    STATE.add_result(
        "check-run",
        DetectorResult(
            score=0.1,
            verdict=Verdict.fail,
            plain_english="Failure detected.",
            details={},
        ),
        detector_slug="psi",
    )
    resp = client.post("/dashboard/checks/check-run/run")
    assert resp.status_code == 200
    assert "result-fragment" in resp.text
    assert "fail" in resp.text


def test_dashboard_run_post_unknown_check() -> None:
    """Re-run on unknown check returns 200 empty-state fragment, not 500."""
    resp = client.post("/dashboard/checks/no-such-check/run")
    assert resp.status_code == 200
