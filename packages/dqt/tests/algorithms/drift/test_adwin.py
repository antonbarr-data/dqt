# packages/dqt/tests/algorithms/drift/test_adwin.py
# Ref: Bifet & Gavalda (2007) SDM — Learning from Time-Changing Data with Adaptive Windowing
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.drift.adwin import ADWINDetector
    return ADWINDetector()


def test_adwin_stable_stream_pass(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert result.verdict == Verdict.pass_
    assert result.score < 0.5


def test_adwin_large_shift_detected(detector, normal_df, shifted_df):
    state = detector.fit(normal_df)
    result = detector.score(shifted_df, state)
    assert result.verdict != Verdict.pass_
    assert result.score >= 0.5


def test_adwin_score_bounded(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_adwin_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.0, "adwin") == Verdict.pass_
    assert compute_verdict(1.0, "adwin") == Verdict.fail


def test_adwin_details_stable(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert "drift_detected" in result.details
    assert result.details["drift_detected"] is False
    assert "ref_mean" in result.details
    assert "curr_mean" in result.details
    assert "n_windows_checked" in result.details


def test_adwin_details_drift_uses_window_means(detector, normal_df, shifted_df):
    """When drift detected, details must use window_before/window_after — not ref/curr means."""
    state = detector.fit(normal_df)
    result = detector.score(shifted_df, state)
    assert result.details["drift_detected"] is True
    assert "window_before" in result.details, "drift details must have window_before"
    assert "window_after" in result.details, "drift details must have window_after"
    assert "ref_mean" not in result.details, "ref_mean must not appear in drift details"
    assert result.details["window_before"] != result.details["window_after"], (
        "window_before and window_after must differ on drift"
    )


@pytest.mark.unit
def test_adwin_plain_english_shows_different_means_on_drift():
    """When drift detected, plain_english must show different window_before and window_after."""
    import re
    from dqt.algorithms.drift.adwin import ADWINDetector

    rng = np.random.default_rng(42)
    ref = pd.DataFrame({"value": rng.normal(100.0, 5.0, 200)})
    curr = pd.DataFrame({"value": rng.normal(150.0, 5.0, 200)})

    det = ADWINDetector()
    state = det.fit(ref)
    result = det.score(curr, state)

    assert result.score == 1.0, "Expected drift detected"
    assert "window_before=" in result.plain_english
    assert "window_after=" in result.plain_english
    # Extract the two numeric values from the parenthesised section
    nums = re.findall(r"[-\d.]+", result.plain_english.split("(")[1])
    assert len(nums) == 2
    assert float(nums[0]) != float(nums[1]), (
        f"window_before and window_after should differ: {result.plain_english}"
    )
