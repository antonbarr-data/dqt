# packages/dqt/tests/algorithms/timeseries/test_page_hinkley.py
# Ref: Hinkley (1971) Biometrika — Inference about the change-point from cumulative sum tests
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.timeseries.page_hinkley import PageHinkleyDetector
    return PageHinkleyDetector()


def test_ph_stable_series_pass(detector, timeseries_df):
    ref = timeseries_df.iloc[:300].reset_index(drop=True)
    curr = timeseries_df.iloc[300:340].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.verdict == Verdict.pass_
    assert result.score < 0.5


def test_ph_large_shift_fail(detector, timeseries_df):
    ref = timeseries_df.iloc[:300].reset_index(drop=True)
    curr = timeseries_df.iloc[300:340].copy().reset_index(drop=True)
    curr["value"] += 30.0
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.verdict == Verdict.fail
    assert result.score >= 1.0


def test_ph_score_non_negative(detector, timeseries_df):
    ref = timeseries_df.iloc[:200].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(timeseries_df.iloc[200:250].reset_index(drop=True), state)
    assert result.score >= 0.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_ph_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.3, "page_hinkley") == Verdict.pass_
    assert compute_verdict(0.7, "page_hinkley") == Verdict.warn
    assert compute_verdict(1.5, "page_hinkley") == Verdict.fail


def test_ph_details_present(detector, timeseries_df):
    ref = timeseries_df.iloc[:200].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(timeseries_df.iloc[200:250].reset_index(drop=True), state)
    assert "ph_statistic" in result.details
    assert "lambda_threshold" in result.details
    assert "ref_mean" in result.details
