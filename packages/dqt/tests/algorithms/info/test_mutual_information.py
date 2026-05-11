# packages/dqt/tests/algorithms/info/test_mutual_information.py
# Ref: Cover & Thomas (2006) Elements of Information Theory — mutual information
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.info.mutual_information import MutualInformationDetector
    return MutualInformationDetector()


def test_mi_identical_distributions_pass(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert result.verdict == Verdict.pass_
    assert result.score > 0.50


def test_mi_shifted_distribution_fail(detector, normal_df, shifted_df):
    state = detector.fit(normal_df)
    result = detector.score(shifted_df, state)
    assert result.verdict == Verdict.fail
    assert result.score < 0.30


def test_mi_score_bounded(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_mi_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.80, "mutual_information") == Verdict.pass_
    assert compute_verdict(0.40, "mutual_information") == Verdict.warn
    assert compute_verdict(0.20, "mutual_information") == Verdict.fail


def test_mi_details_present(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert "normalized_mi" in result.details
    assert "n_bins" in result.details
