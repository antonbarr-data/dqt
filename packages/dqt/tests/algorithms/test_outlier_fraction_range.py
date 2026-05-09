import numpy as np
import pandas as pd
import pytest
from dqt.algorithms.outliers_uni.outlier_fraction_range import OutlierFractionRangeDetector


def make_history(values):
    return pd.DataFrame({"outlier_fraction": values})


def make_current(value):
    return pd.DataFrame({"outlier_fraction": [value]})


def test_within_range_scores_zero():
    det = OutlierFractionRangeDetector()
    history = make_history([0.02, 0.03, 0.025, 0.028, 0.022, 0.031, 0.019, 0.027, 0.033, 0.024])
    state = det.fit(history)
    result = det.score(make_current(0.025), state)
    assert result.score == pytest.approx(0.0)
    assert result.verdict.value == "pass"


def test_well_above_range_scores_nonzero_and_fails():
    det = OutlierFractionRangeDetector()
    history = make_history([0.02, 0.03, 0.025, 0.028, 0.022, 0.031, 0.019, 0.027, 0.033, 0.024])
    state = det.fit(history)
    result = det.score(make_current(0.50), state)  # way above historical range
    assert result.score > 0.0
    assert result.verdict.value in ("warn", "fail")


def test_all_methods_fit_without_error():
    history = make_history([0.01, 0.02, 0.015, 0.018, 0.012, 0.022, 0.009, 0.017, 0.021, 0.014])
    for method in ("iqr", "percentile", "zscore"):
        det = OutlierFractionRangeDetector()
        state = det.fit(history, method=method)
        assert "lower" in state
        assert "upper" in state
        assert state["lower"] >= 0.0
        assert state["upper"] <= 1.0


def test_state_contains_n_history():
    det = OutlierFractionRangeDetector()
    history = make_history([0.02, 0.03, 0.025, 0.028, 0.022])
    state = det.fit(history)
    assert state["n_history"] == 5


def test_insufficient_history_raises():
    det = OutlierFractionRangeDetector()
    with pytest.raises(ValueError, match="at least 3"):
        det.fit(make_history([0.02]))  # only 1 point


def test_score_details_contain_bounds():
    det = OutlierFractionRangeDetector()
    history = make_history([0.02, 0.03, 0.025, 0.028, 0.022, 0.031, 0.019, 0.027])
    state = det.fit(history)
    result = det.score(make_current(0.09), state)
    assert "lower" in result.details
    assert "upper" in result.details
    assert "current_fraction" in result.details


def test_collapsed_range_does_not_exceed_one():
    """When all history is constant, score must be in [0, 1]."""
    det = OutlierFractionRangeDetector()
    history = make_history([0.02, 0.02, 0.02, 0.02, 0.02])
    state = det.fit(history)
    result = det.score(make_current(0.50), state)
    assert 0.0 <= result.score <= 1.0


def test_all_nan_current_raises():
    """All-NaN current data must raise ValueError, not IndexError."""
    det = OutlierFractionRangeDetector()
    history = make_history([0.02, 0.03, 0.025, 0.028, 0.022])
    state = det.fit(history)
    current = pd.DataFrame({"outlier_fraction": [float("nan"), float("nan")]})
    with pytest.raises(ValueError, match="no non-NaN"):
        det.score(current, state)
