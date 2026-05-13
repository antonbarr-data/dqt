"""Live integration tests for the Databricks adapter.

Skipped unless DQT_TEST_DATABRICKS_DSN is set in the environment.

Set: DQT_TEST_DATABRICKS_DSN=databricks://token:<token>@<host>?http_path=<http_path>&catalog=<catalog>
"""
import os

import pytest

pytestmark = pytest.mark.adapter

SKIP = pytest.mark.skipif(
    not os.environ.get("DQT_TEST_DATABRICKS_DSN"),
    reason="DQT_TEST_DATABRICKS_DSN not set",
)


def _adapter():
    from urllib.parse import parse_qs, urlparse

    from dqt.adapters.databricks import DatabricksAdapter

    dsn = os.environ["DQT_TEST_DATABRICKS_DSN"]
    parsed = urlparse(dsn)
    qs = parse_qs(parsed.query)

    # databricks://token:<token>@<host>?http_path=...&catalog=...&schema=...
    return DatabricksAdapter(
        server_hostname=parsed.hostname,
        http_path=qs.get("http_path", [""])[0],
        access_token=parsed.password or "",
        catalog=qs.get("catalog", ["hive_metastore"])[0],
        schema=qs.get("schema", ["default"])[0],
    )


@SKIP
def test_health_check_passes():
    result = _adapter().health_check()
    assert result.passed, [s for s in result.steps if s.status not in ("pass", "skip")]


@SKIP
def test_health_check_has_six_steps():
    steps = _adapter().health_check().steps
    assert len(steps) == 6
    assert [s.name for s in steps] == [
        "tcp_reach", "auth", "info_schema", "sample_select", "latency_probe", "clock_skew"
    ]


@SKIP
def test_list_schemas_returns_list():
    schemas = _adapter().list_schemas()
    assert isinstance(schemas, list)
    assert len(schemas) > 0


@SKIP
def test_sample_returns_dataframe():
    import pandas as pd

    adapter = _adapter()
    schemas = adapter.list_schemas()
    tables = adapter.list_tables(schemas[0])
    if not tables:
        pytest.skip("no tables found in first schema")
    df = adapter.sample(schemas[0], tables[0], n=100)
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
