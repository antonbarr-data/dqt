# packages/dqt/tests/algorithms/drift/test_wasserstein.py
# Ref: Kantorovich (1942); Wasserstein (1969) — earth-mover distance
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.drift.wasserstein import Wasserstein1Detector
    return Wasserstein1Detector()


def test_wasserstein_same_distribution_pass(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert result.verdict == Verdict.pass_
    assert result.score < 0.20


def test_wasserstein_large_shift_fail(detector, normal_df, shifted_df):
    state = detector.fit(normal_df)
    result = detector.score(shifted_df, state)
    assert result.verdict == Verdict.fail
    assert result.score > 0.50


def test_wasserstein_score_bounded(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert 0.0 <= result.score
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_wasserstein_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.05, "wasserstein_1") == Verdict.pass_
    assert compute_verdict(0.30, "wasserstein_1") == Verdict.warn
    assert compute_verdict(0.70, "wasserstein_1") == Verdict.fail


def test_wasserstein_details_present(detector, normal_df, shifted_df):
    state = detector.fit(normal_df)
    result = detector.score(shifted_df, state)
    assert "raw_distance" in result.details
    assert "ref_std" in result.details
