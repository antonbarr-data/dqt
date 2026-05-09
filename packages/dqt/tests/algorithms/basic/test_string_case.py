import pandas as pd
import pytest


def _agg(violations: int, total: int = 1000) -> pd.DataFrame:
    return pd.DataFrame([{"violation_count": violations, "total_count": total}])


def test_string_case_pass():
    from dqt.algorithms.basic.string_case import StringCaseDetector
    d = StringCaseDetector(case="upper")
    result = d.score(_agg(0), d.fit(pd.DataFrame()))
    assert result.verdict.value == "pass"


def test_string_case_fail():
    from dqt.algorithms.basic.string_case import StringCaseDetector
    d = StringCaseDetector(case="upper")
    result = d.score(_agg(50), d.fit(pd.DataFrame()))
    assert result.verdict.value == "fail"


def test_string_case_sql_upper():
    from dqt.algorithms.basic.string_case import StringCaseDetector
    d = StringCaseDetector(case="upper")
    aggs = d.get_aggregations("name")
    sql = aggs[0].sql
    assert "upper" in sql.lower()


def test_string_case_invalid_raises():
    from dqt.algorithms.basic.string_case import StringCaseDetector
    with pytest.raises(ValueError, match="case"):
        StringCaseDetector(case="mixed_weird")
