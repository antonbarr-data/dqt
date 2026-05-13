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


def test_always_passing_check_appears_in_metrics():
    """Checks with no incidents must still appear in Prometheus output."""
    from dqt.metrics.prometheus import build_metrics_text
    store = MemoryStore()
    check_id = uuid4()
    store.save_run(_run(Verdict.pass_, 0.1, check_id=check_id))
    # No incident saved — this is the always-passing case
    text = build_metrics_text(store)
    assert str(check_id) in text
    assert "dqt_check_score" in text
    assert "dqt_check_verdict" in text
    assert f'dqt_check_verdict{{check_id="{check_id}",detector_slug="ks_pvalue"}} 0' in text


def test_runs_total_counts_all_runs():
    """dqt_check_runs_total must reflect the actual number of saved runs."""
    from dqt.metrics.prometheus import build_metrics_text
    store = MemoryStore()
    check_id = uuid4()
    for _ in range(5):
        store.save_run(_run(Verdict.pass_, 0.05, check_id=check_id))
    text = build_metrics_text(store)
    assert f'dqt_check_runs_total{{check_id="{check_id}",detector_slug="ks_pvalue"}} 5' in text


def test_build_metrics_uses_list_check_ids():
    """build_metrics_text must call list_check_ids(), not access _runs directly."""
    from unittest.mock import MagicMock
    from dqt.metrics.prometheus import build_metrics_text

    mock_store = MagicMock()
    check_id = uuid4()
    mock_store.list_check_ids.return_value = [check_id]
    now = datetime.now(timezone.utc)
    mock_store.list_runs.return_value = [MagicMock(
        detector_slug="ks_pvalue",
        verdict=Verdict.pass_,
        score=0.1,
        finished_at=now,
    )]
    text = build_metrics_text(mock_store)
    mock_store.list_check_ids.assert_called_once()
    assert str(check_id) in text
