import pandas as pd
import pytest


def _agg(null_count: int, total: int = 1000) -> pd.DataFrame:
    return pd.DataFrame([{"null_count": null_count, "total_count": total}])


def test_null_fraction_pass():
    from dqt.algorithms.basic.null_fraction import NullFractionDetector
    d = NullFractionDetector()
    result = d.score(_agg(5), d.fit(pd.DataFrame()))
    assert result.verdict.value == "pass"


def test_null_fraction_warn():
    from dqt.algorithms.basic.null_fraction import NullFractionDetector
    d = NullFractionDetector()
    result = d.score(_agg(15), d.fit(pd.DataFrame()))
    assert result.verdict.value == "warn"


def test_null_fraction_fail():
    from dqt.algorithms.basic.null_fraction import NullFractionDetector
    d = NullFractionDetector()
    result = d.score(_agg(60), d.fit(pd.DataFrame()))
    assert result.verdict.value == "fail"


def test_null_fraction_zero_total():
    from dqt.algorithms.basic.null_fraction import NullFractionDetector
    d = NullFractionDetector()
    result = d.score(pd.DataFrame([{"null_count": 0, "total_count": 0}]), d.fit(pd.DataFrame()))
    assert result.score == 0.0
