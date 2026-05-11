# packages/dqt/tests/algorithms/timeseries/test_bocpd.py
# Ref: Adams & MacKay (2007) arXiv:0710.3742 — Bayesian Online Changepoint Detection
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict
from dqt.algorithms.timeseries.bocpd import BOCPDDetector


@pytest.fixture()
def detector():
    from dqt.algorithms.timeseries.bocpd import BOCPDDetector
    return BOCPDDetector()


def test_bocpd_no_changepoint_pass(detector, timeseries_df):
    ref = timeseries_df.iloc[:200].reset_index(drop=True)
    curr = timeseries_df.iloc[200:250].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.score < 0.80
    assert result.verdict != Verdict.fail


def test_bocpd_clear_changepoint_detected(detector):
    rng = np.random.default_rng(42)
    before = rng.normal(0, 1, 100)
    after = rng.normal(20, 1, 50)
    ref = pd.DataFrame({"value": before})
    curr = pd.DataFrame({"value": after})
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.score > 0.50
    assert result.verdict != Verdict.pass_


def test_bocpd_score_bounded(detector, timeseries_df):
    ref = timeseries_df.iloc[:200].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(timeseries_df.iloc[200:230].reset_index(drop=True), state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_bocpd_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.30, "bocpd") == Verdict.pass_
    assert compute_verdict(0.65, "bocpd") == Verdict.warn
    assert compute_verdict(0.90, "bocpd") == Verdict.fail


def test_bocpd_details_present(detector, timeseries_df):
    ref = timeseries_df.iloc[:200].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(timeseries_df.iloc[200:230].reset_index(drop=True), state)
    assert "max_changepoint_prob" in result.details
    assert "ref_mean" in result.details
    assert "ref_std" in result.details


@pytest.mark.unit
def test_bocpd_detects_level_shift():
    """BOCPD must detect a +30% level shift in the current window."""
    rng = np.random.default_rng(42)
    baseline = rng.normal(100.0, 5.0, 100)
    shifted = rng.normal(130.0, 5.0, 50)

    ref = pd.DataFrame({"value": baseline})
    curr = pd.DataFrame({"value": shifted})

    det = BOCPDDetector()
    state = det.fit(ref)
    result = det.score(curr, state)

    assert result.score >= 0.50, (
        f"Expected changepoint prob >= 0.50 on +30% shift, got {result.score:.4f}"
    )


@pytest.mark.unit
def test_bocpd_stable_data_passes():
    """BOCPD must not trigger on stable data."""
    rng = np.random.default_rng(0)
    ref = pd.DataFrame({"value": rng.normal(50.0, 3.0, 100)})
    curr = pd.DataFrame({"value": rng.normal(50.0, 3.0, 50)})

    det = BOCPDDetector()
    state = det.fit(ref)
    result = det.score(curr, state)

    assert result.score < 0.50, f"Expected pass on stable data, got {result.score:.4f}"
