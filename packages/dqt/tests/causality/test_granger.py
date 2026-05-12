# packages/dqt/tests/causality/test_granger.py
# Ref: Granger (1969) Econometrica — Investigating Causal Relations
import inspect

import numpy as np
import pandas as pd
import pytest
from dqt.causality import granger_pairwise, GrangerReport, GrangerEdge


@pytest.fixture()
def causal_df():
    """X causes Y with a 2-step lag; no reverse causality."""
    rng = np.random.default_rng(42)
    n = 120
    x = rng.normal(0, 1, n)
    y = 0.8 * np.roll(x, 2) + rng.normal(0, 0.2, n)
    return pd.DataFrame({"x": x, "y": y})


@pytest.fixture()
def independent_df():
    rng = np.random.default_rng(7)
    n = 120
    return pd.DataFrame({"a": rng.normal(0, 1, n), "b": rng.normal(10, 2, n)})


def test_granger_detects_x_causes_y(causal_df):
    report = granger_pairwise(causal_df, max_lag=3)
    x_to_y = next((e for e in report.edges if e.cause == "x" and e.effect == "y"), None)
    assert x_to_y is not None
    assert x_to_y.significant


def test_granger_independent_series_not_significant(independent_df):
    report = granger_pairwise(independent_df, max_lag=2)
    for edge in report.edges:
        assert not edge.significant


def test_granger_report_structure(causal_df):
    report = granger_pairwise(causal_df, max_lag=2)
    assert isinstance(report, GrangerReport)
    assert len(report.edges) == 2  # x->y and y->x
    d = report.to_dict()
    assert "n_pairs_tested" in d
    assert "edges" in d
    for e in d["edges"]:
        assert "cause" in e
        assert "effect" in e
        assert "adjusted_p_value" in e
        assert "significant" in e


def test_granger_too_few_rows():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    with pytest.raises(ValueError, match="at least"):
        granger_pairwise(df)


def test_granger_significant_edges_filter(causal_df):
    report = granger_pairwise(causal_df, max_lag=3)
    assert len(report.significant_edges) >= 1
    assert all(e.significant for e in report.significant_edges)


def test_granger_pairwise_has_no_events_param():
    """events param was removed because it annotated without conditioning — dishonest API."""
    from dqt.causality import granger_pairwise
    sig = inspect.signature(granger_pairwise)
    assert "events" not in sig.parameters, (
        "granger_pairwise must not have an 'events' parameter — "
        "it annotated without conditioning, which is misleading"
    )
    assert "period" not in sig.parameters, (
        "granger_pairwise must not have a 'period' parameter — "
        "it was removed together with 'events' in v0.4.3"
    )
