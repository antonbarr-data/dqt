import math
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.schema.schema_checks import SchemaChangeDetector
    return SchemaChangeDetector()


def schema_df(columns: list[tuple[str, str]]) -> pd.DataFrame:
    return pd.DataFrame([{"col_name": c, "data_type": t} for c, t in columns])


def test_no_schema_change(detector):
    schema = [("id", "integer"), ("amount", "numeric"), ("status", "text")]
    df = schema_df(schema)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.score == 0.0
    assert result.verdict == Verdict.pass_


def test_column_added(detector):
    ref = schema_df([("id", "integer"), ("amount", "numeric")])
    curr = schema_df([("id", "integer"), ("amount", "numeric"), ("new_col", "text")])
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.score == 1.0
    assert result.verdict == Verdict.fail
    assert "new_col" in result.plain_english


def test_column_removed(detector):
    ref = schema_df([("id", "integer"), ("amount", "numeric"), ("status", "text")])
    curr = schema_df([("id", "integer"), ("amount", "numeric")])
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.score == 1.0
    assert result.verdict == Verdict.fail
    assert "status" in result.plain_english


def test_type_changed(detector):
    ref = schema_df([("id", "integer"), ("amount", "numeric")])
    curr = schema_df([("id", "integer"), ("amount", "text")])
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.score == 1.0
    assert result.verdict == Verdict.fail


@given(n=st.integers(1, 20))
@settings(max_examples=50)
def test_schema_stability_no_change(n):
    from dqt.algorithms.schema.schema_checks import SchemaChangeDetector
    cols = [(f"col_{i}", "text") for i in range(n)]
    df = schema_df(cols)
    det = SchemaChangeDetector()
    state = det.fit(df)
    result = det.score(df, state)
    assert result.score == 0.0
    assert not math.isnan(result.score)


def test_schema_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.0, "schema_change") == Verdict.pass_
    assert compute_verdict(1.0, "schema_change") == Verdict.fail
