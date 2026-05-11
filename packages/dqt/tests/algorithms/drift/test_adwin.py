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


def test_adwin_details_present(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert "drift_detected" in result.details
    assert "ref_mean" in result.details
    assert "curr_mean" in result.details
    assert "n_windows_checked" in result.details
