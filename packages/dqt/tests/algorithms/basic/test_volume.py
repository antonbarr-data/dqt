import math
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.basic.volume import VolumeDetector
    return VolumeDetector()


def agg(count: int) -> pd.DataFrame:
    return pd.DataFrame([{"row_count": count}])


def test_volume_no_change(detector):
    ref = agg(1000)
    state = detector.fit(ref)
    result = detector.score(ref, state)
    assert result.score == pytest.approx(0.0)
    assert result.verdict == Verdict.pass_


def test_volume_warn(detector):
    ref = agg(1000)
    state = detector.fit(ref)
    curr = agg(880)
    result = detector.score(curr, state)
    assert result.score == pytest.approx(0.12, abs=0.01)
    assert result.verdict == Verdict.warn


def test_volume_fail(detector):
    ref = agg(1000)
    state = detector.fit(ref)
    curr = agg(700)
    result = detector.score(curr, state)
    assert result.score == pytest.approx(0.30, abs=0.01)
    assert result.verdict == Verdict.fail


@given(
    ref_count=st.integers(1, 10_000),
    curr_count=st.integers(1, 10_000),
)
@settings(max_examples=200)
def test_volume_stability(ref_count, curr_count):
    from dqt.algorithms.basic.volume import VolumeDetector
    ref = agg(ref_count)
    curr = agg(curr_count)
    det = VolumeDetector()
    state = det.fit(ref)
    result = det.score(curr, state)
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)
    assert result.score >= 0.0


def test_volume_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.05, "volume_change_ratio") == Verdict.pass_
    assert compute_verdict(0.15, "volume_change_ratio") == Verdict.warn
    assert compute_verdict(0.30, "volume_change_ratio") == Verdict.fail
