# packages/dqt/tests/algorithms/timeseries/test_holt_winters.py
# Ref: Holt (1957); Winters (1960) Management Science
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.timeseries.holt_winters import HoltWintersDetector
    return HoltWintersDetector(period=7)


def test_hw_clean_continuation_pass(detector, timeseries_df):
    ref = timeseries_df.iloc[:300].reset_index(drop=True)
    curr = timeseries_df.iloc[300:350].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.verdict != Verdict.fail


def test_hw_spiked_series_detected(detector, timeseries_df):
    ref = timeseries_df.iloc[:300].reset_index(drop=True)
    curr = timeseries_df.iloc[300:350].copy().reset_index(drop=True)
    curr.iloc[::3, 0] += 30.0
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.details["anomaly_fraction"] > 0.0
    assert result.verdict != Verdict.pass_


def test_hw_score_bounded(detector, timeseries_df):
    ref = timeseries_df.iloc[:200].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(timeseries_df.iloc[200:250].reset_index(drop=True), state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_hw_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.02, "holt_winters") == Verdict.pass_
    assert compute_verdict(0.07, "holt_winters") == Verdict.warn
    assert compute_verdict(0.15, "holt_winters") == Verdict.fail


def test_hw_details_present(detector, timeseries_df):
    ref = timeseries_df.iloc[:200].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(timeseries_df.iloc[200:250].reset_index(drop=True), state)
    assert "anomaly_fraction" in result.details
    assert "n_anomalies" in result.details
    assert "period" in result.details
