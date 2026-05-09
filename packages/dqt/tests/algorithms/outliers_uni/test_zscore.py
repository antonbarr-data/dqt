import math
import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.outliers_uni.zscore import ZScoreDetector
    return ZScoreDetector()


def test_zscore_detects_spike(detector):
    # 19 clean points + spike of 50.0 → fraction = 1/20 = 5% > fail threshold (5%)
    rng = np.random.default_rng(42)
    data = rng.normal(0, 1, 19)
    data = np.append(data, 50.0)
    df = pd.DataFrame({"value": data})
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.details["outlier_fraction"] > 0
    assert result.verdict != Verdict.pass_


def test_zscore_no_false_positives(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert result.verdict == Verdict.pass_


def test_zscore_many_spikes_fail(detector):
    # Fit on clean reference, score on contaminated current to expose the spikes.
    rng = np.random.default_rng(7)
    clean_ref = rng.normal(0, 1, 900)
    clean_curr = rng.normal(0, 1, 90)
    spikes = np.full(10, 100.0)
    df_ref = pd.DataFrame({"value": clean_ref})
    df_curr = pd.DataFrame({"value": np.concatenate([clean_curr, spikes])})
    state = detector.fit(df_ref)
    result = detector.score(df_curr, state)
    assert result.verdict == Verdict.fail


@given(
    values=st.lists(
        st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
        min_size=10, max_size=500,
    )
)
@settings(max_examples=100)
def test_zscore_stability(values):
    from dqt.algorithms.outliers_uni.zscore import ZScoreDetector
    df = pd.DataFrame({"value": values})
    det = ZScoreDetector()
    state = det.fit(df)
    result = det.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_zscore_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.005, "zscore_outlier_fraction") == Verdict.pass_
    assert compute_verdict(0.02, "zscore_outlier_fraction") == Verdict.warn
    assert compute_verdict(0.08, "zscore_outlier_fraction") == Verdict.fail
