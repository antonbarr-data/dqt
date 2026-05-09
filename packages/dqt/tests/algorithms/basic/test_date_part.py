import pandas as pd
import pytest


def _agg(missing: int, total_buckets: int = 30) -> pd.DataFrame:
    return pd.DataFrame([{"missing_buckets": missing, "total_buckets": total_buckets}])


def test_date_part_pass():
    from dqt.algorithms.basic.date_part import DatePartCompletenessDetector
    d = DatePartCompletenessDetector(granularity="day", lookback_days=30)
    result = d.score(_agg(0), d.fit(pd.DataFrame()))
    assert result.verdict.value == "pass"


def test_date_part_fail():
    from dqt.algorithms.basic.date_part import DatePartCompletenessDetector
    d = DatePartCompletenessDetector(granularity="day", lookback_days=30)
    result = d.score(_agg(5), d.fit(pd.DataFrame()))
    assert result.verdict.value == "fail"


def test_date_part_aggregations():
    from dqt.algorithms.basic.date_part import DatePartCompletenessDetector
    d = DatePartCompletenessDetector(granularity="day", lookback_days=30, col="created_at")
    aggs = d.get_aggregations("created_at")
    assert len(aggs) == 2


def test_date_part_invalid_granularity():
    from dqt.algorithms.basic.date_part import DatePartCompletenessDetector
    with pytest.raises(ValueError, match="granularity"):
        DatePartCompletenessDetector(granularity="century")
