import math
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st
from dqt.algorithms._base import Verdict


def agg(violation_count: int, total: int) -> pd.DataFrame:
    return pd.DataFrame([{"violation_count": violation_count, "total_count": total}])


@pytest.fixture()
def gt_det():
    from dqt.algorithms.basic.column_pairs import ColumnPairComparisonDetector
    return ColumnPairComparisonDetector(col_a="list_price", col_b="sale_price", operator=">")

def test_pair_comparison_pass(gt_det):
    df = agg(0, 1000)
    state = gt_det.fit(df)
    result = gt_det.score(df, state)
    assert result.score == 0.0
    assert result.verdict == Verdict.pass_

def test_pair_comparison_fail(gt_det):
    df = agg(20, 1000)
    state = gt_det.fit(df)
    result = gt_det.score(df, state)
    assert result.verdict == Verdict.fail

def test_pair_comparison_sql_uses_operator(gt_det):
    exprs = gt_det.get_aggregations("ignored")
    sql_text = " ".join(e.sql for e in exprs)
    assert "list_price" in sql_text
    assert "sale_price" in sql_text
    assert ">" in sql_text

@pytest.mark.parametrize("op", [">", ">=", "<", "<=", "=", "!="])
def test_pair_comparison_operators(op):
    from dqt.algorithms.basic.column_pairs import ColumnPairComparisonDetector
    det = ColumnPairComparisonDetector(col_a="a", col_b="b", operator=op)
    exprs = det.get_aggregations("ignored")
    assert any(op in e.sql for e in exprs)


@pytest.fixture()
def comp_det():
    from dqt.algorithms.basic.column_pairs import CompositeUniquenessDetector
    return CompositeUniquenessDetector(key_columns=["order_id", "line_item"])

def test_composite_unique_pass(comp_det):
    df = pd.DataFrame([{"total_count": 1000, "distinct_count": 1000}])
    state = comp_det.fit(df)
    result = comp_det.score(df, state)
    assert result.score == 0.0
    assert result.verdict == Verdict.pass_

def test_composite_unique_fail(comp_det):
    df = pd.DataFrame([{"total_count": 1000, "distinct_count": 980}])
    state = comp_det.fit(df)
    result = comp_det.score(df, state)
    assert result.score == pytest.approx(0.02, abs=0.001)
    assert result.verdict == Verdict.fail


@given(violations=st.integers(0, 1000), total=st.integers(1, 1000))
@settings(max_examples=200)
def test_column_pair_stability(violations, total):
    from dqt.algorithms.basic.column_pairs import ColumnPairComparisonDetector
    violations = min(violations, total)
    det = ColumnPairComparisonDetector(col_a="a", col_b="b", operator=">")
    df = agg(violations, total)
    state = det.fit(df)
    result = det.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)


def test_column_pairs_stat_scale_verdicts():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.0,   "column_pair_violation") == Verdict.pass_
    assert compute_verdict(0.002, "column_pair_violation") == Verdict.warn
    assert compute_verdict(0.02,  "column_pair_violation") == Verdict.fail
    assert compute_verdict(0.0,   "composite_uniqueness_violation") == Verdict.pass_
    assert compute_verdict(0.002, "composite_uniqueness_violation") == Verdict.warn
    assert compute_verdict(0.02,  "composite_uniqueness_violation") == Verdict.fail
