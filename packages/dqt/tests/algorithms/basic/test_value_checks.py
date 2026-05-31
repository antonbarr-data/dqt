import math
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st
from dqt.algorithms._base import Verdict


def agg(out_of_rule: int, total: int) -> pd.DataFrame:
    return pd.DataFrame([{"violation_count": out_of_rule, "total_count": total}])


@pytest.fixture()
def range_det():
    from dqt.algorithms.basic.value_checks import ValueInRangeDetector
    return ValueInRangeDetector(min_value=0.0, max_value=100.0)

def test_value_in_range_pass(range_det):
    df = agg(0, 1000)
    state = range_det.fit(df)
    result = range_det.score(df, state)
    assert result.score == 0.0
    assert result.verdict == Verdict.pass_

def test_value_in_range_fail(range_det):
    df = agg(50, 1000)
    state = range_det.fit(df)
    result = range_det.score(df, state)
    assert result.score == pytest.approx(0.05)
    assert result.verdict == Verdict.fail

def test_value_in_range_sql_uses_bounds(range_det):
    exprs = range_det.get_aggregations("price")
    sql_text = " ".join(e.sql for e in exprs)
    assert "0.0" in sql_text and "100.0" in sql_text


@pytest.fixture()
def set_det():
    from dqt.algorithms.basic.value_checks import SetMembershipDetector
    return SetMembershipDetector(allowed_values={"active", "inactive", "pending"})

def test_set_membership_pass(set_det):
    df = agg(0, 1000)
    state = set_det.fit(df)
    result = set_det.score(df, state)
    assert result.verdict == Verdict.pass_

def test_set_membership_fail(set_det):
    df = agg(20, 1000)
    state = set_det.fit(df)
    result = set_det.score(df, state)
    assert result.verdict == Verdict.fail

def test_set_exclusion_pass():
    from dqt.algorithms.basic.value_checks import SetExclusionDetector
    det = SetExclusionDetector(forbidden_values={"deleted", "banned"})
    df = agg(0, 1000)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.pass_

def test_set_exclusion_fail():
    from dqt.algorithms.basic.value_checks import SetExclusionDetector
    det = SetExclusionDetector(forbidden_values={"deleted", "banned"})
    df = agg(15, 1000)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.fail

def test_regex_match_pass():
    from dqt.algorithms.basic.value_checks import RegexMatchDetector
    det = RegexMatchDetector(pattern=r"^[A-Z]{2}\d{4}$")
    df = agg(0, 500)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.pass_

def test_regex_match_fail():
    from dqt.algorithms.basic.value_checks import RegexMatchDetector
    det = RegexMatchDetector(pattern=r"^[A-Z]{2}\d{4}$")
    df = agg(10, 500)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.fail

def test_string_length_pass():
    from dqt.algorithms.basic.value_checks import StringLengthRangeDetector
    det = StringLengthRangeDetector(min_len=2, max_len=50)
    df = agg(0, 1000)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.pass_

def test_string_length_fail():
    from dqt.algorithms.basic.value_checks import StringLengthRangeDetector
    det = StringLengthRangeDetector(min_len=2, max_len=50)
    df = agg(20, 1000)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.fail

def test_date_format_pass():
    from dqt.algorithms.basic.value_checks import DateFormatDetector
    det = DateFormatDetector(date_format="%Y-%m-%d")
    df = agg(0, 500)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.pass_

def test_date_format_fail():
    from dqt.algorithms.basic.value_checks import DateFormatDetector
    det = DateFormatDetector(date_format="%Y-%m-%d")
    df = agg(25, 500)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.fail

@given(violations=st.integers(0, 1000), total=st.integers(1, 1000))
@settings(max_examples=200)
def test_value_checks_stability(violations, total):
    from dqt.algorithms.basic.value_checks import ValueInRangeDetector
    violations = min(violations, total)
    det = ValueInRangeDetector(min_value=0.0, max_value=100.0)
    df = pd.DataFrame([{"violation_count": violations, "total_count": total}])
    state = det.fit(df)
    result = det.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)

def test_value_in_range_date_sql():
    from dqt.algorithms.basic.value_checks import ValueInRangeDetector
    det = ValueInRangeDetector(min_value="2024-01-01", max_value="2025-12-31", value_type="date")
    exprs = det.get_aggregations("event_date")
    sql = " ".join(e.sql for e in exprs)
    assert "'2024-01-01'" in sql and "'2025-12-31'" in sql
    # Numeric literals must not appear
    assert "2024.0" not in sql

def test_value_in_range_date_clickhouse_sql():
    from dqt.algorithms.basic.value_checks import ValueInRangeDetector
    det = ValueInRangeDetector(min_value="2024-01-01", max_value="2025-12-31", value_type="date")
    exprs = det.get_aggregations("event_date", dialect="clickhouse")
    sql = " ".join(e.sql for e in exprs)
    assert "toDate('2024-01-01')" in sql

def test_value_in_range_string_sql():
    from dqt.algorithms.basic.value_checks import ValueInRangeDetector
    det = ValueInRangeDetector(min_value="apple", max_value="mango", value_type="string")
    exprs = det.get_aggregations("fruit")
    sql = " ".join(e.sql for e in exprs)
    assert "'apple'" in sql and "'mango'" in sql

def test_value_in_range_unbounded_date():
    from dqt.algorithms.basic.value_checks import ValueInRangeDetector
    det = ValueInRangeDetector(max_value="2025-12-31", value_type="date")
    exprs = det.get_aggregations("event_date")
    sql = exprs[0].sql
    assert "2025-12-31" in sql
    assert "<" not in sql  # no lower bound

def test_value_in_range_numeric_backward_compat():
    from dqt.algorithms.basic.value_checks import ValueInRangeDetector
    # Old-style: no value_type, float bounds
    det = ValueInRangeDetector(min_value=0.0, max_value=100.0)
    exprs = det.get_aggregations("price")
    sql = " ".join(e.sql for e in exprs)
    assert "0.0" in sql and "100.0" in sql

def test_value_checks_stat_scale_verdicts():
    from dqt.algorithms._base import compute_verdict
    for slug in ("value_in_range_violation", "set_membership_violation",
                 "set_exclusion_violation", "regex_match_violation",
                 "string_length_violation", "date_format_violation"):
        assert compute_verdict(0.0,   slug) == Verdict.pass_
        assert compute_verdict(0.002, slug) == Verdict.warn
        assert compute_verdict(0.02,  slug) == Verdict.fail
