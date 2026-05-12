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


def test_schema_change_detects_rename():
    """When a column is renamed, details should contain 'renamed_columns'."""
    from dqt.algorithms.schema.schema_checks import SchemaChangeDetector

    ref = schema_df([("user_id", "integer"), ("created_at", "text"), ("amount", "numeric")])
    curr = schema_df([("user_id", "integer"), ("created_ts", "text"), ("amount", "numeric")])

    det = SchemaChangeDetector()
    state = det.fit(ref)
    result = det.score(curr, state)

    assert result.score > 0.0
    renames = result.details.get("renamed_columns", [])
    assert len(renames) >= 1
    rename = renames[0]
    assert rename["from"] == "created_at"
    assert rename["to"] == "created_ts"


def test_schema_rename_not_in_removed_or_added():
    """Renamed columns should not appear in added/removed lists."""
    from dqt.algorithms.schema.schema_checks import SchemaChangeDetector

    ref = schema_df([("id", "integer"), ("amt", "numeric")])
    curr = schema_df([("id", "integer"), ("amount", "numeric")])

    det = SchemaChangeDetector()
    state = det.fit(ref)
    result = det.score(curr, state)

    # "amt" -> "amount" is within Levenshtein 3 but dtype same: should be a rename
    renames = result.details.get("renamed_columns", [])
    rename_froms = {r["from"] for r in renames}
    rename_tos = {r["to"] for r in renames}
    # either detected as rename OR as add/remove, but not both
    if renames:
        assert "amt" not in result.details.get("removed", [])
        assert "amount" not in result.details.get("added", [])
