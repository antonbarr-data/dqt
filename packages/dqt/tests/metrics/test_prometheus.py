# packages/dqt/tests/metrics/test_prometheus.py
"""Tests for the Prometheus metrics builder."""
from datetime import datetime, timezone
from uuid import uuid4
import pytest
from dqt.algorithms._base import Verdict
from dqt.store._protocol import RunResult
from dqt.store.memory import MemoryStore


def _run(verdict: Verdict, score: float, check_id=None):
    now = datetime.now(timezone.utc)
    return RunResult(
        run_id=uuid4(), check_id=check_id or uuid4(),
        detector_slug="ks_pvalue", detector_version="1",
        started_at=now, finished_at=now,
        verdict=verdict, score=score, plain_english="ok", details={},
    )


def test_build_metrics_returns_text():
    from dqt.metrics.prometheus import build_metrics_text
    store = MemoryStore()
    check_id = uuid4()
    store.save_run(_run(Verdict.pass_, 0.1, check_id=check_id))
    # Save an incident so the exporter picks it up
    from dqt.store._protocol import Incident
    now = datetime.now(timezone.utc)
    store.save_incident(Incident(
        incident_id=uuid4(), check_id=check_id,
        run_id=uuid4(), detector_slug="ks_pvalue",
        severity=Verdict.fail, opened_at=now,
        score=0.1, status="open",
    ))
    text = build_metrics_text(store)
    assert "dqt_check_score" in text
    assert "dqt_check_runs_total" in text
    assert "# HELP" in text
    assert "# TYPE" in text


def test_verdict_to_int():
    from dqt.metrics.prometheus import _verdict_to_int
    assert _verdict_to_int(Verdict.pass_) == 0
    assert _verdict_to_int(Verdict.warn) == 1
    assert _verdict_to_int(Verdict.fail) == 2


def test_build_metrics_empty_store():
    from dqt.metrics.prometheus import build_metrics_text
    store = MemoryStore()
    text = build_metrics_text(store)
    assert isinstance(text, str)
    assert "# HELP dqt_check_score" in text
