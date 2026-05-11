# packages/dqt/tests/algorithms/pattern/test_benford.py
# Ref: Benford (1938) Proc. Am. Philos. Soc. — first-digit law for naturally occurring numbers
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.pattern.benford import BenfordDetector
    return BenfordDetector()


def _benford_sample(n: int, seed: int = 42) -> pd.DataFrame:
    """Generate data that follows Benford's Law (log-uniform)."""
    rng = np.random.default_rng(seed)
    vals = 10 ** rng.uniform(0, 4, n)
    return pd.DataFrame({"value": vals})


def _uniform_first_digits(n: int) -> pd.DataFrame:
    """Generate data with uniform first digits — strongly violates Benford's."""
    rng = np.random.default_rng(99)
    first_digits = rng.integers(1, 10, n)
    rest = rng.uniform(0, 1, n)
    vals = (first_digits + rest).astype(float)
    return pd.DataFrame({"value": vals})


def test_benford_conforming_data_pass(detector):
    df = _benford_sample(5000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.verdict == Verdict.pass_
    assert result.score < 0.95


def test_benford_violation_detected(detector):
    df_benford = _benford_sample(5000)
    df_uniform = _uniform_first_digits(5000)
    state = detector.fit(df_benford)
    result = detector.score(df_uniform, state)
    assert result.verdict != Verdict.pass_
    assert result.details["p_value"] < 0.05


def test_benford_score_bounded(detector):
    df = _benford_sample(1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)


def test_benford_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.90, "benford_law_fit") == Verdict.pass_
    assert compute_verdict(0.96, "benford_law_fit") == Verdict.warn
    assert compute_verdict(0.995, "benford_law_fit") == Verdict.fail


def test_benford_details_present(detector):
    df = _benford_sample(2000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert "p_value" in result.details
    assert "chi2_statistic" in result.details
    assert "digit_fractions" in result.details
