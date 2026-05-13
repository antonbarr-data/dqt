"""Live integration tests for the ClickHouse adapter.

Skipped unless DQT_TEST_CLICKHOUSE_DSN is set in the environment.

Set: DQT_TEST_CLICKHOUSE_DSN=clickhouse://user:pass@host:8123/database
"""
import os

import pytest

pytestmark = pytest.mark.adapter

SKIP = pytest.mark.skipif(
    not os.environ.get("DQT_TEST_CLICKHOUSE_DSN"),
    reason="DQT_TEST_CLICKHOUSE_DSN not set",
)


def _adapter():
    from urllib.parse import urlparse

    from dqt.adapters.clickhouse import ClickHouseAdapter

    dsn = os.environ["DQT_TEST_CLICKHOUSE_DSN"]
    parsed = urlparse(dsn)
    kwargs = {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 8123,
    }
    if parsed.username:
        kwargs["username"] = parsed.username
    if parsed.password:
        kwargs["password"] = parsed.password
    db = parsed.path.lstrip("/")
    if db:
        kwargs["database"] = db
    return ClickHouseAdapter(**kwargs)


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
