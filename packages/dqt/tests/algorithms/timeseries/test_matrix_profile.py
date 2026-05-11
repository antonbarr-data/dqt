# packages/dqt/tests/algorithms/timeseries/test_matrix_profile.py
# Ref: Yeh et al. (2016) ICDM — Matrix Profile I
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.timeseries.matrix_profile import MatrixProfileDetector
    return MatrixProfileDetector(window=7)


def test_mp_stable_series_pass(detector, timeseries_df):
    ref = timeseries_df.iloc[:280].reset_index(drop=True)
    curr = timeseries_df.iloc[280:350].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.verdict == Verdict.pass_


def test_mp_discord_detected(detector, timeseries_df):
    ref = timeseries_df.iloc[:280].reset_index(drop=True)
    curr = timeseries_df.iloc[280:350].copy().reset_index(drop=True)
    curr.iloc[30:37, 0] = 500.0
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.details["discord_fraction"] > 0.0
    assert result.verdict != Verdict.pass_


def test_mp_score_bounded(detector, timeseries_df):
    ref = timeseries_df.iloc[:200].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(timeseries_df.iloc[200:270].reset_index(drop=True), state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_mp_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.02, "matrix_profile") == Verdict.pass_
    assert compute_verdict(0.07, "matrix_profile") == Verdict.warn
    assert compute_verdict(0.15, "matrix_profile") == Verdict.fail


def test_mp_details_present(detector, timeseries_df):
    ref = timeseries_df.iloc[:200].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(timeseries_df.iloc[200:270].reset_index(drop=True), state)
    assert "discord_fraction" in result.details
    assert "distance_threshold" in result.details
    assert "window" in result.details
    assert "backend" in result.details


def test_mp_slug_registered():
    import dqt  # noqa: F401
    from dqt.algorithms._registry import registry
    assert registry.get("matrix_profile") is not None
