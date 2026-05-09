import pandas as pd
import pytest
from datetime import datetime, timezone, timedelta


def _agg(seconds_behind: float) -> pd.DataFrame:
    latest = datetime.now(timezone.utc) - timedelta(seconds=seconds_behind)
    return pd.DataFrame([{"latest_ts": latest}])


def test_freshness_pass():
    from dqt.algorithms.basic.freshness import FreshnessDetector
    d = FreshnessDetector(warn_seconds=3600, fail_seconds=86400)
    state = d.fit(pd.DataFrame())
    result = d.score(_agg(60), state)
    assert result.verdict.value == "pass"


def test_freshness_warn():
    from dqt.algorithms.basic.freshness import FreshnessDetector
    d = FreshnessDetector(warn_seconds=3600, fail_seconds=86400)
    state = d.fit(pd.DataFrame())
    result = d.score(_agg(7200), state)
    assert result.verdict.value == "warn"


def test_freshness_fail():
    from dqt.algorithms.basic.freshness import FreshnessDetector
    d = FreshnessDetector(warn_seconds=3600, fail_seconds=86400)
    state = d.fit(pd.DataFrame())
    result = d.score(_agg(90000), state)
    assert result.verdict.value == "fail"


def test_freshness_aggregations():
    from dqt.algorithms.basic.freshness import FreshnessDetector
    d = FreshnessDetector(col="created_at")
    aggs = d.get_aggregations("created_at")
    assert len(aggs) == 1
    assert "MAX" in aggs[0].sql.upper()
