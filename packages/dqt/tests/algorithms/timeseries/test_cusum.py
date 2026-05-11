# packages/dqt/tests/algorithms/timeseries/test_cusum.py
# Ref: Page (1954) Biometrika — Continuous inspection schemes (CUSUM)
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.timeseries.cusum import CUSUMDetector
    return CUSUMDetector()


def test_cusum_stable_series_pass(detector, timeseries_df):
    ref = timeseries_df.iloc[:300].reset_index(drop=True)
    curr = timeseries_df.iloc[300:340].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.verdict == Verdict.pass_
    assert result.score < 1.0


def test_cusum_large_mean_shift_fail(detector, timeseries_df):
    ref = timeseries_df.iloc[:300].reset_index(drop=True)
    curr = timeseries_df.iloc[300:340].copy().reset_index(drop=True)
    curr["value"] += 20.0
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.verdict == Verdict.fail
    assert result.score > 2.0


def test_cusum_score_non_negative(detector, timeseries_df):
    ref = timeseries_df.iloc[:200].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(timeseries_df.iloc[200:250].reset_index(drop=True), state)
    assert result.score >= 0.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_cusum_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.5, "cusum") == Verdict.pass_
    assert compute_verdict(1.5, "cusum") == Verdict.warn
    assert compute_verdict(3.0, "cusum") == Verdict.fail


def test_cusum_details_present(detector, timeseries_df):
    ref = timeseries_df.iloc[:200].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(timeseries_df.iloc[200:250].reset_index(drop=True), state)
    assert "cusum_hi" in result.details
    assert "cusum_lo" in result.details
    assert "ref_mean" in result.details
    assert "ref_std" in result.details
