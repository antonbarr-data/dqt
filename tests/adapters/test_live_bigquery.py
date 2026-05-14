"""Live integration tests for BigQuery adapter.

Requires env vars: GCP_SA_KEY_BIGQUERY (JSON string), GCP_PROJECT_ID
Skipped automatically when credentials are not set.
"""
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

_REPO = Path(__file__).parents[2]
sys.path.insert(0, str(_REPO / "packages" / "dqt" / "src"))

pytestmark = pytest.mark.adapter


@pytest.fixture(scope="module")
def adapter(skip_no_bigquery):
    from dqt.adapters.bigquery import BigQueryAdapter

    return BigQueryAdapter(
        project=os.environ["GCP_PROJECT_ID"],
        credentials_json=os.environ["GCP_SA_KEY_BIGQUERY"],
    )


def test_health_check(adapter):
    result = adapter.health_check()
    assert result["status"] in ("ok", "healthy", "pass")


def test_list_schemas(adapter):
    schemas = adapter.list_schemas()
    assert isinstance(schemas, list)
    assert len(schemas) >= 1


def test_describe_columns(adapter):
    # INFORMATION_SCHEMA.TABLES is available in every BigQuery project
    cols = adapter.describe_columns("INFORMATION_SCHEMA", "TABLES")
    assert isinstance(cols, list)
    assert len(cols) >= 1
    assert all("name" in c for c in cols)


def test_sample(adapter):
    df = adapter.sample("INFORMATION_SCHEMA", "TABLES", n=10)
    assert isinstance(df, pd.DataFrame)
    assert len(df) >= 1


def test_aggregate(adapter):
    agg = adapter.aggregate("INFORMATION_SCHEMA", "TABLES", metrics=["count"])
    assert "count" in agg or "row_count" in agg


def test_end_to_end_null_fraction(adapter):
    from dqt.algorithms._registry import registry

    import dqt.algorithms.basic  # noqa: F401 — registers the detector

    df = adapter.sample("INFORMATION_SCHEMA", "TABLES", n=100)
    det = registry.get("null_fraction")()
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict in ("pass", "warn", "fail")


def test_end_to_end_mad_outlier(adapter):
    from dqt.algorithms._registry import registry

    import dqt.algorithms.outliers_uni  # noqa: F401 — registers the detector

    df = adapter.sample("INFORMATION_SCHEMA", "TABLES", n=100)
    numeric_cols = df.select_dtypes("number").columns
    if len(numeric_cols) == 0:
        pytest.skip("No numeric columns in INFORMATION_SCHEMA.TABLES sample")
    col_df = df[[numeric_cols[0]]].rename(columns={numeric_cols[0]: "value"})
    det = registry.get("mad_outlier_fraction")()
    state = det.fit(col_df)
    result = det.score(col_df, state)
    assert result.verdict in ("pass", "warn", "fail")
