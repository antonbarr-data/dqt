import math
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.referential.referential import ReferentialIntegrityDetector
    return ReferentialIntegrityDetector()


def agg(orphan_count: int, total: int) -> pd.DataFrame:
    return pd.DataFrame([{"orphan_count": orphan_count, "total_count": total}])


def test_no_orphans(detector):
    df = agg(0, 1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.score == pytest.approx(1.0)
    assert result.verdict == Verdict.pass_


def test_few_orphans_warn(detector):
    # 15/1000 orphans → rate = 0.985 → warn
    df = agg(15, 1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.score == pytest.approx(0.985, abs=1e-6)
    assert result.verdict == Verdict.warn


def test_many_orphans_fail(detector):
    df = agg(60, 1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.score < 0.95
    assert result.verdict == Verdict.fail


@given(orphans=st.integers(0, 1000), total=st.integers(1, 1000))
@settings(max_examples=200)
def test_referential_stability(orphans, total):
    from dqt.algorithms.referential.referential import ReferentialIntegrityDetector
    orphans = min(orphans, total)
    df = agg(orphans, total)
    det = ReferentialIntegrityDetector()
    state = det.fit(df)
    result = det.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)


def test_referential_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.995, "referential_integrity_rate") == Verdict.pass_
    assert compute_verdict(0.985, "referential_integrity_rate") == Verdict.warn
    assert compute_verdict(0.90, "referential_integrity_rate") == Verdict.fail
