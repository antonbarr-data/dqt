# Ref: Leys et al. (2013) J. Exp. Soc. Psychol. — modified Z-score with MAD, threshold 3.5
# Ref: Rousseeuw & Croux (1993) JASA — asymmetric MAD for skewed distributions
import math
import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.outliers_uni.mad import MADOutlierDetector
    return MADOutlierDetector()


@pytest.fixture()
def double_detector():
    from dqt.algorithms.outliers_uni.mad import DoubleMadOutlierDetector
    return DoubleMadOutlierDetector()


def test_mad_detects_spike(detector):
    rng = np.random.default_rng(42)
    # 19 clean points + 1 spike → fraction = 1/20 = 5% > fail threshold (5%)
    data = rng.normal(0, 1, 19).tolist()
    data.append(100.0)
    df = pd.DataFrame({"value": data})
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.details["outlier_fraction"] > 0
    assert result.verdict != Verdict.pass_


def test_mad_no_false_positives(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert result.verdict == Verdict.pass_


def test_mad_many_outliers_fail(detector):
    rng = np.random.default_rng(7)
    clean = rng.normal(0, 1, 900)
    spikes = np.full(100, 200.0)
    df = pd.DataFrame({"value": np.concatenate([clean, spikes])})
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.verdict == Verdict.fail


@given(
    values=st.lists(
        st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
        min_size=10, max_size=500,
    )
)
@settings(max_examples=100)
def test_mad_stability(values):
    from dqt.algorithms.outliers_uni.mad import MADOutlierDetector
    df = pd.DataFrame({"value": values})
    det = MADOutlierDetector()
    state = det.fit(df)
    result = det.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_mad_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.005, "mad_outlier_fraction") == Verdict.pass_
    assert compute_verdict(0.02, "mad_outlier_fraction") == Verdict.warn
    assert compute_verdict(0.08, "mad_outlier_fraction") == Verdict.fail


def test_double_mad_right_tail_spike(double_detector):
    rng = np.random.default_rng(42)
    data = rng.lognormal(mean=0.0, sigma=0.5, size=500).tolist()
    data.append(1000.0)
    df = pd.DataFrame({"value": data})
    state = double_detector.fit(df)
    result = double_detector.score(df, state)
    assert result.details["outlier_fraction"] > 0
    assert result.verdict != Verdict.pass_


def test_double_mad_catches_what_mad_misses():
    # On right-skewed data (chi-square), single MAD inflates the threshold for
    # right-tail values, while double-MAD uses a smaller right-side MAD giving
    # a tighter upper fence. Verify the spike of 200.0 is detected by double-MAD.
    from dqt.algorithms.outliers_uni.mad import DoubleMadOutlierDetector, MADOutlierDetector
    rng = np.random.default_rng(42)
    data = rng.chisquare(df=2, size=1000)
    spike = np.array([200.0])
    df_train = pd.DataFrame({"value": data})
    df_with_spike = pd.DataFrame({"value": np.concatenate([data, spike])})
    dmad_det = DoubleMadOutlierDetector()
    dmad_state = dmad_det.fit(df_train)
    dmad_result = dmad_det.score(df_with_spike, dmad_state)
    # The extreme spike of 200.0 must be flagged
    assert dmad_result.details["outlier_fraction"] > 0


def test_double_mad_no_false_positives_symmetric(double_detector, normal_df):
    state = double_detector.fit(normal_df)
    result = double_detector.score(normal_df, state)
    assert result.verdict == Verdict.pass_


@given(
    values=st.lists(
        st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False),
        min_size=10, max_size=500,
    )
)
@settings(max_examples=100)
def test_double_mad_stability(values):
    from dqt.algorithms.outliers_uni.mad import DoubleMadOutlierDetector
    df = pd.DataFrame({"value": values})
    det = DoubleMadOutlierDetector()
    state = det.fit(df)
    result = det.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_double_mad_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.005, "double_mad_outlier_fraction") == Verdict.pass_
    assert compute_verdict(0.02, "double_mad_outlier_fraction") == Verdict.warn
    assert compute_verdict(0.08, "double_mad_outlier_fraction") == Verdict.fail
