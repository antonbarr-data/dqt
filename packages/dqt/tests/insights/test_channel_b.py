import numpy as np
import pandas as pd
import pytest
from dqt.insights.channel_b import analyze, ChannelBReport


def _panel(n: int = 60) -> pd.DataFrame:
    """Synthetic panel: revenue driven by ad_spend with 1-period lag."""
    rng = np.random.default_rng(42)
    ad_spend = rng.normal(100, 10, n)
    revenue = np.roll(ad_spend, 1) * 1.5 + rng.normal(0, 5, n)
    revenue[0] = revenue[1]  # fix roll artifact
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    return pd.DataFrame({"revenue": revenue, "ad_spend": ad_spend}, index=idx)


def test_analyze_returns_channel_b_report():
    panel = _panel()
    report = analyze("revenue", panel)
    assert isinstance(report, ChannelBReport)
    assert isinstance(report.business_drivers, list)
    assert isinstance(report.ruled_out, list)
    assert len(report.estimated_contribution) == 2


def test_analyze_empty_panel_returns_empty_report():
    report = analyze("revenue", pd.DataFrame())
    assert report.business_drivers == []
    assert report.mix_shift is None


def test_analyze_auto_routes_to_pcmci_for_many_columns():
    rng = np.random.default_rng(0)
    idx = pd.date_range("2024-01-01", periods=60, freq="D")
    cols = {f"metric_{i}": rng.normal(0, 1, 60) for i in range(5)}
    panel = pd.DataFrame(cols, index=idx)
    report = analyze("metric_0", panel)
    assert isinstance(report, ChannelBReport)
