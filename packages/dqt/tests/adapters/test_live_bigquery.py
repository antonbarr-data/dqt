"""Live integration tests for the BigQuery adapter.

Skipped unless DQT_TEST_BIGQUERY_PROJECT is set in the environment.

Set:
  DQT_TEST_BIGQUERY_PROJECT=my-gcp-project
  GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json  (optional; ADC used if absent)
"""
import os

import pytest

pytestmark = pytest.mark.adapter

SKIP = pytest.mark.skipif(
    not os.environ.get("DQT_TEST_BIGQUERY_PROJECT"),
    reason="DQT_TEST_BIGQUERY_PROJECT not set",
)


def _adapter():
    from dqt.adapters.bigquery import BigQueryAdapter

    return BigQueryAdapter(
        project=os.environ["DQT_TEST_BIGQUERY_PROJECT"],
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
        pytest.skip("no tables found in first dataset")
    df = adapter.sample(schemas[0], tables[0], n=100)
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
