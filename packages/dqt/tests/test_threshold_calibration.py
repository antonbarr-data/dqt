# packages/dqt/tests/test_threshold_calibration.py
"""Tests for calibrate_from_history() and ThresholdDriftResult."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest

import dqt
from dqt.algorithms._calibration import ThresholdDriftResult, calibrate_from_history
from dqt.algorithms._base import Verdict
from dqt.store._protocol import RunResult
from dqt.store.memory import MemoryStore


def _make_check(slug: str = "completeness") -> dqt.Check:
    return dqt.Check(
        schema_name="public",
        table_name="orders",
        column_name="amount",
        detector_slug=slug,
    )


def _make_run_result(check: dqt.Check, verdict: Verdict, score: float) -> RunResult:
    now = datetime.now(timezone.utc)
    return RunResult(
        check_id=check.id,
        detector_slug=check.detector_slug,
        started_at=now,
        finished_at=now,
        verdict=verdict,
        score=score,
        plain_english="ok",
    )


def _store_with_pass_runs(check: dqt.Check, scores: list[float]) -> MemoryStore:
    store = MemoryStore()
    for score in scores:
        store.save_run(_make_run_result(check, Verdict.pass_, score))
    return store


def test_returns_none_when_insufficient_history():
    check = _make_check()
    store = _store_with_pass_runs(check, [0.1] * 10)  # fewer than min_samples=50
    result = calibrate_from_history(check, store)
    assert result is None


def test_returns_result_when_sufficient_history():
    check = _make_check()
    store = _store_with_pass_runs(check, [0.1] * 60)
    result = calibrate_from_history(check, store)
    assert isinstance(result, ThresholdDriftResult)
    assert result.n_pass_runs == 60


def test_suggested_threshold_is_high_percentile_of_pass_scores():
    check = _make_check()
    scores = [0.05] * 100  # all scores at 0.05
    store = _store_with_pass_runs(check, scores)
    result = calibrate_from_history(check, store, target_fpr=0.001)
    assert result is not None
    # The (1 - 0.001)*100 = 99.9th percentile of a constant distribution is the constant
    assert abs(result.suggested_threshold - 0.05) < 0.01


def test_ignores_non_pass_runs():
    check = _make_check()
    store = MemoryStore()
    # 60 pass runs with score 0.1
    for _ in range(60):
        store.save_run(_make_run_result(check, Verdict.pass_, 0.1))
    # 20 fail runs with score 0.9 — must not pollute the calibration
    for _ in range(20):
        store.save_run(_make_run_result(check, Verdict.fail, 0.9))

    result = calibrate_from_history(check, store)
    assert result is not None
    assert result.n_pass_runs == 60
    assert result.suggested_threshold < 0.5


def test_drift_fraction_computed_relative_to_current_threshold():
    check = dqt.Check(
        schema_name="public",
        table_name="orders",
        column_name="amount",
        detector_slug="completeness",
        warn_threshold=0.1,  # explicit override
    )
    store = _store_with_pass_runs(check, [0.2] * 100)
    result = calibrate_from_history(check, store)
    assert result is not None
    assert result.current_threshold == 0.1
    # suggested ~0.2, current=0.1 → drift = |0.2-0.1|/0.1 = 1.0
    assert result.drift_fraction > 0.5
    assert result.is_significant is True


def test_not_significant_when_drift_below_10pct():
    check = dqt.Check(
        schema_name="public",
        table_name="orders",
        column_name="amount",
        detector_slug="completeness",
        warn_threshold=0.200,
    )
    # Scores at 0.201 — drift = |0.201-0.200|/0.200 = 0.005, well below 10%
    store = _store_with_pass_runs(check, [0.201] * 100)
    result = calibrate_from_history(check, store)
    assert result is not None
    assert result.is_significant is False


def test_uses_stat_scale_default_when_no_check_threshold():
    from dqt.algorithms._scales import STAT_SCALES
    check = _make_check("completeness")
    # No explicit warn_threshold — should fall back to STAT_SCALES
    assert check.warn_threshold is None
    store = _store_with_pass_runs(check, [0.0] * 100)
    result = calibrate_from_history(check, store)
    assert result is not None
    scale = STAT_SCALES.get("completeness")
    if scale is not None:
        assert result.current_threshold == scale.warn_threshold


def test_exported_from_public_api():
    assert hasattr(dqt, "ThresholdDriftResult")
    assert hasattr(dqt, "calibrate_from_history")


def test_min_samples_override():
    check = _make_check()
    store = _store_with_pass_runs(check, [0.1] * 20)
    # Default min_samples=50 → None
    assert calibrate_from_history(check, store) is None
    # Overridden min_samples=10 → result
    result = calibrate_from_history(check, store, min_samples=10)
    assert isinstance(result, ThresholdDriftResult)
