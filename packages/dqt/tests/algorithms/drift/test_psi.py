# packages/dqt/tests/algorithms/drift/test_psi.py
# Ref: PSI (credit risk industry standard) — symmetric KL divergence over equal-frequency bins
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.drift.psi import PSIDetector
    return PSIDetector()


def test_psi_same_distribution_pass(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert result.verdict == Verdict.pass_
    assert result.score < 0.10


def test_psi_large_shift_fail(detector, normal_df, shifted_df):
    state = detector.fit(normal_df)
    result = detector.score(shifted_df, state)
    assert result.verdict == Verdict.fail
    assert result.score > 0.20


def test_psi_score_non_negative(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert result.score >= 0.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_psi_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.05, "psi") == Verdict.pass_
    assert compute_verdict(0.15, "psi") == Verdict.warn
    assert compute_verdict(0.25, "psi") == Verdict.fail


def test_psi_details_present(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert "n_bins" in result.details
    assert "psi" in result.details
