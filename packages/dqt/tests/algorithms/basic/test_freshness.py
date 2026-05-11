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


def test_freshness_handles_string_timestamp():
    """Regression: DuckDB aggregate() may return timestamps as strings."""
    from dqt.algorithms.basic.freshness import FreshnessDetector
    detector = FreshnessDetector(warn_seconds=3600, fail_seconds=86400)
    state = detector.fit(pd.DataFrame())
    # Simulate a string timestamp 30 minutes ago (DuckDB CSV path returns strings)
    recent_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    df = pd.DataFrame({"latest_ts": [recent_ts]})
    result = detector.score(df, state)
    assert "could not be parsed" not in result.plain_english
    assert result.score < 3600


def test_freshness_handles_naive_string_timestamp():
    """String timestamps without timezone info should not bail."""
    from dqt.algorithms.basic.freshness import FreshnessDetector
    detector = FreshnessDetector(warn_seconds=3600, fail_seconds=86400)
    state = detector.fit(pd.DataFrame())
    df = pd.DataFrame({"latest_ts": ["2020-01-01 00:00:00"]})
    result = detector.score(df, state)
    assert "could not be parsed" not in result.plain_english
    assert result.verdict.value == "fail"
