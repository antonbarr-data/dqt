# packages/dqt/tests/adapters/test_snowflake_adapter.py
"""Snowflake adapter integration tests.

Skipped unless DQT_SNOWFLAKE_DSN env var is set.
Set via GitHub Actions secret DQT_SNOWFLAKE_DSN; enable job via var DQT_SNOWFLAKE_ENABLED=true.

DSN format: snowflake://user:password@account/database/schema?warehouse=WH&role=ROLE
"""
import os
import pytest

pytestmark = pytest.mark.adapter


def _dsn() -> str:
    dsn = os.environ.get("DQT_SNOWFLAKE_DSN", "")
    if not dsn:
        pytest.skip("DQT_SNOWFLAKE_DSN not set — skipping Snowflake tests")
    return dsn


@pytest.fixture(scope="module")
def adapter():
    from dqt.adapters.snowflake import SnowflakeAdapter
    return SnowflakeAdapter(dsn=_dsn())


def test_health_check(adapter):
    result = adapter.health_check()
    assert result.ok, f"Snowflake health check failed: {result}"


def test_list_schemas(adapter):
    schemas = adapter.list_schemas()
    assert isinstance(schemas, list)
    assert len(schemas) > 0


def test_list_tables(adapter):
    schemas = adapter.list_schemas()
    assert len(schemas) > 0
    tables = adapter.list_tables(schemas[0])
    assert isinstance(tables, list)


def test_describe_columns(adapter):
    schemas = adapter.list_schemas()
    for schema in schemas:
        tables = adapter.list_tables(schema)
        if tables:
            cols = adapter.describe_columns(schema, tables[0])
            assert len(cols) > 0
            return
    pytest.skip("No tables found in any schema")


def test_sample(adapter):
    schemas = adapter.list_schemas()
    for schema in schemas:
        tables = adapter.list_tables(schema)
        if tables:
            df = adapter.sample(schema, tables[0], n=10)
            assert len(df) <= 10
            return
    pytest.skip("No tables found in any schema")


def test_cost_estimate_respected(adapter):
    """Adapter must refuse queries exceeding max_bytes_per_query."""
    from dqt.adapters.snowflake import SnowflakeAdapter
    frugal = SnowflakeAdapter(dsn=_dsn(), max_bytes_per_query=1)
    schemas = adapter.list_schemas()
    for schema in schemas:
        tables = adapter.list_tables(schema)
        if tables:
            with pytest.raises(Exception, match="cost|bytes|budget"):
                frugal.sample(schema, tables[0], n=1000)
            return
    pytest.skip("No tables found")
