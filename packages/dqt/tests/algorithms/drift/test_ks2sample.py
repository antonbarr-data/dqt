# Ref: Kolmogorov (1933), Smirnov (1948) — two-sample KS test via scipy.stats.ks_2samp
import math
import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.drift.ks2sample import KS2SampleDetector
    return KS2SampleDetector()


def test_ks_same_distribution(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert result.verdict == Verdict.pass_
    assert result.score < 0.95  # 1 - p_value should be low


def test_ks_detects_drift(detector, normal_df, shifted_df):
    state = detector.fit(normal_df)
    result = detector.score(shifted_df, state)
    assert result.verdict != Verdict.pass_
    assert result.details["p_value"] < 0.01


def test_ks_no_false_positive(detector):
    rng = np.random.default_rng(1)
    ref = pd.DataFrame({"value": rng.normal(10, 2, 1000)})
    curr = pd.DataFrame({"value": rng.normal(10.05, 2, 1000)})
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.verdict == Verdict.pass_


@given(
    n=st.integers(min_value=20, max_value=500),
    shift=st.floats(min_value=-5.0, max_value=5.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_ks_stability(n, shift):
    from dqt.algorithms.drift.ks2sample import KS2SampleDetector
    rng = np.random.default_rng(42)
    ref = pd.DataFrame({"value": rng.normal(0, 1, n)})
    curr = pd.DataFrame({"value": rng.normal(shift, 1, n)})
    det = KS2SampleDetector()
    state = det.fit(ref)
    result = det.score(curr, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_ks_empty_current_returns_pass():
    from dqt.algorithms.drift.ks2sample import KS2SampleDetector
    rng = np.random.default_rng(42)
    ref = pd.DataFrame({"value": rng.normal(0, 1, 100)})
    curr = pd.DataFrame({"value": pd.array([None, None, None], dtype="Float64")})
    det = KS2SampleDetector()
    state = det.fit(ref)
    result = det.score(curr, state)
    assert result.verdict == Verdict.pass_
    assert result.score == 0.0


def test_ks_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.90, "ks_pvalue") == Verdict.pass_
    assert compute_verdict(0.96, "ks_pvalue") == Verdict.warn
    assert compute_verdict(0.995, "ks_pvalue") == Verdict.fail
