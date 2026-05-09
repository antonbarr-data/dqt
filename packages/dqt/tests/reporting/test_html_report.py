import numpy as np
import pandas as pd
import pytest
from dqt.profiling.profiler import DataProfiler
from dqt.reporting.html_report import profiling_report, quality_report, save_report
from unittest.mock import MagicMock


def test_profiling_report_generates_html():
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "amount": rng.normal(100, 15, 200),
        "status": ["active" if i % 3 != 0 else None for i in range(200)],
        "id": range(200),
    })
    mock_adapter = MagicMock()
    mock_adapter.sample.return_value = df
    profiler = DataProfiler(mock_adapter)
    profile = profiler.profile("public", "orders")
    html = profiling_report(profile, title="Test Report")
    assert "<!DOCTYPE html>" in html
    assert "amount" in html
    assert "status" in html
    assert len(html) > 1000


def test_quality_report_generates_html():
    results = [
        {"check": "completeness_rate", "table": "public.orders", "column": "amount",
         "verdict": "pass", "score": 0.01, "plain_english": "98% complete"},
        {"check": "null_fraction", "table": "public.orders", "column": "status",
         "verdict": "warn", "score": 0.33, "plain_english": "33% null values"},
    ]
    html = quality_report(results, dataset_name="orders", title="Test DQ Report")
    assert "<!DOCTYPE html>" in html
    assert "PASS" in html or "pass" in html.lower()
    assert "WARN" in html or "warn" in html.lower()
    assert len(html) > 500


def test_save_report(tmp_path):
    html = "<html><body>test</body></html>"
    out = tmp_path / "report.html"
    save_report(html, str(out))
    assert out.read_text() == html
