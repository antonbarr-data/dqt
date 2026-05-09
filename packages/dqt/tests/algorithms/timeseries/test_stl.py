# Ref: Cleveland et al. (1990) JASA — Seasonal-Trend decomposition using Loess
import math
import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.timeseries.stl import STLAnomalyDetector
    return STLAnomalyDetector(period=7)


def test_stl_detects_spike(detector, timeseries_df):
    ref = timeseries_df.iloc[:300].reset_index(drop=True)
    curr = timeseries_df.iloc[300:365].copy().reset_index(drop=True)
    curr.iloc[10, 0] += 50.0
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.score > 3.0
    assert result.verdict != Verdict.pass_


def test_stl_clean_continuation(detector, timeseries_df):
    # Score clean continuation data against the fitted reference.
    # STL residuals on a short window can have higher max-Z due to edge effects,
    # so we verify the score is below the fail threshold (no severe anomaly).
    ref = timeseries_df.iloc[:300].reset_index(drop=True)
    curr = timeseries_df.iloc[300:350].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.verdict != Verdict.fail


def test_stl_constant_series():
    from dqt.algorithms.timeseries.stl import STLAnomalyDetector
    data = [10.0] * 56
    df = pd.DataFrame({"value": data})
    det = STLAnomalyDetector(period=7)
    state = det.fit(df)
    result = det.score(pd.DataFrame({"value": [10.0] * 28}), state)
    assert result.score == pytest.approx(0.0, abs=1.0)
    assert not math.isnan(result.score)


@given(
    n_ref=st.integers(min_value=4, max_value=15),
    n_curr=st.integers(min_value=3, max_value=8),
    period=st.integers(min_value=2, max_value=5),
    noise=st.floats(min_value=0.01, max_value=5.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=30, deadline=15_000)
def test_stl_stability(n_ref, n_curr, period, noise):
    from dqt.algorithms.timeseries.stl import STLAnomalyDetector
    rng = np.random.default_rng(42)
    n_total_ref = n_ref * period * 2
    n_total_curr = n_curr * period
    ref_vals = np.sin(2 * np.pi * np.arange(n_total_ref) / period) + rng.normal(0, noise, n_total_ref)
    curr_vals = np.sin(2 * np.pi * np.arange(n_total_curr) / period) + rng.normal(0, noise, n_total_curr)
    ref_df = pd.DataFrame({"value": ref_vals})
    curr_df = pd.DataFrame({"value": curr_vals})
    det = STLAnomalyDetector(period=period)
    state = det.fit(ref_df)
    result = det.score(curr_df, state)
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)
    assert result.score >= 0.0


def test_stl_rejects_too_short_current():
    from dqt.algorithms.timeseries.stl import STLAnomalyDetector
    det = STLAnomalyDetector(period=7)
    # 56 points = valid reference (> 2*7+1=15)
    state = det.fit(pd.DataFrame({"value": [10.0] * 56}))
    with pytest.raises(ValueError, match="requires at least"):
        det.score(pd.DataFrame({"value": [10.0] * 5}), state)


def test_stl_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(2.0, "stl_residual_zscore") == Verdict.pass_
    assert compute_verdict(4.0, "stl_residual_zscore") == Verdict.warn
    assert compute_verdict(6.0, "stl_residual_zscore") == Verdict.fail
