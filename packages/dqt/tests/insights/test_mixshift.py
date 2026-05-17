import pandas as pd
from dqt.insights.mixshift import decompose


def _make_segment_df():
    # Two time windows, two segments (US/EU), metric = avg_order_value
    # Window 1 (before): US 60% share at $100, EU 40% share at $80 -> avg $92
    # Window 2 (after):  US 40% share at $100, EU 60% share at $80 -> avg $88
    # Pure mix shift (no level change): $92 -> $88 = -4.3%
    return pd.DataFrame([
        {"window": "before", "segment": "US", "share": 0.60, "value": 100.0},
        {"window": "before", "segment": "EU", "share": 0.40, "value": 80.0},
        {"window": "after",  "segment": "US", "share": 0.40, "value": 100.0},
        {"window": "after",  "segment": "EU", "share": 0.60, "value": 80.0},
    ])


def test_decompose_detects_mix_shift():
    df = _make_segment_df()
    report = decompose(df, dimension="region")
    assert report is not None
    assert report.dimension == "region"
    assert report.mix_contribution_low < report.mix_contribution_high
    assert len(report.segments) == 2


def test_decompose_mix_contribution_in_range():
    df = _make_segment_df()
    report = decompose(df, dimension="region")
    assert report is not None
    assert 0.0 <= report.mix_contribution_low <= 1.0
    assert 0.0 <= report.mix_contribution_high <= 1.0


def test_decompose_returns_none_when_no_data():
    result = decompose(pd.DataFrame(), dimension="region")
    assert result is None
