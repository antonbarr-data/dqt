"""Live integration tests for the Snowflake adapter.

Skipped unless DQT_TEST_SNOWFLAKE_DSN is set in the environment.

Set: DQT_TEST_SNOWFLAKE_DSN=snowflake://user:pass@account/db/schema
The DSN is parsed into kwargs accepted by snowflake.connector.connect().
"""
import os

import pytest

pytestmark = pytest.mark.adapter

SKIP = pytest.mark.skipif(
    not os.environ.get("DQT_TEST_SNOWFLAKE_DSN"),
    reason="DQT_TEST_SNOWFLAKE_DSN not set",
)


def _adapter():
    from urllib.parse import urlparse

    from dqt.adapters.snowflake import SnowflakeAdapter

    dsn = os.environ["DQT_TEST_SNOWFLAKE_DSN"]
    parsed = urlparse(dsn)
    # snowflake://user:pass@account/database/schema
    path_parts = parsed.path.lstrip("/").split("/")
    kwargs = {
        "user": parsed.username,
        "password": parsed.password,
        "account": parsed.hostname,
    }
    if len(path_parts) >= 1 and path_parts[0]:
        kwargs["database"] = path_parts[0]
    if len(path_parts) >= 2 and path_parts[1]:
        kwargs["schema"] = path_parts[1]
    return SnowflakeAdapter(**kwargs)


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
