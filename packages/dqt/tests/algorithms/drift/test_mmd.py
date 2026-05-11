# Ref: Gretton et al. (2012) JMLR — A Kernel Two-Sample Test (MMD²)
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.drift.mmd import MMDDetector
    return MMDDetector()


def test_mmd_same_distribution_pass(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert result.verdict == Verdict.pass_
    assert result.score < 0.10


def test_mmd_large_shift_fail(detector, normal_df, shifted_df):
    state = detector.fit(normal_df)
    result = detector.score(shifted_df, state)
    assert result.verdict == Verdict.fail
    assert result.score > 0.20


def test_mmd_score_bounded(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_mmd_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.05, "mmd") == Verdict.pass_
    assert compute_verdict(0.12, "mmd") == Verdict.warn
    assert compute_verdict(0.25, "mmd") == Verdict.fail


def test_mmd_details_present(detector, normal_df, shifted_df):
    state = detector.fit(normal_df)
    result = detector.score(shifted_df, state)
    assert "mmd_squared" in result.details
    assert "gamma" in result.details


def test_mmd_symmetric_approx(detector, normal_df, shifted_df):
    state_a = detector.fit(normal_df)
    result_ab = detector.score(shifted_df, state_a)
    state_b = detector.fit(shifted_df)
    result_ba = detector.score(normal_df, state_b)
    assert abs(result_ab.score - result_ba.score) < 0.15
