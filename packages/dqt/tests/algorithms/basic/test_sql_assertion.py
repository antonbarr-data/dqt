import pandas as pd
import pytest


def _agg(violations: int, total: int = 1000) -> pd.DataFrame:
    return pd.DataFrame([{"violation_count": violations, "total_count": total}])


def test_sql_assertion_pass():
    from dqt.algorithms.basic.sql_assertion import SqlAssertionDetector
    d = SqlAssertionDetector(condition="amount > 0")
    result = d.score(_agg(0), d.fit(pd.DataFrame()))
    assert result.verdict.value == "pass"


def test_sql_assertion_fail():
    from dqt.algorithms.basic.sql_assertion import SqlAssertionDetector
    d = SqlAssertionDetector(condition="amount > 0")
    result = d.score(_agg(50), d.fit(pd.DataFrame()))
    assert result.verdict.value == "fail"


def test_sql_assertion_aggregations():
    from dqt.algorithms.basic.sql_assertion import SqlAssertionDetector
    d = SqlAssertionDetector(condition="amount > 0")
    aggs = d.get_aggregations("amount")
    assert any("amount > 0" in a.sql for a in aggs)
