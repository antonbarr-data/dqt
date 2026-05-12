# packages/dqt/tests/adapters/test_databricks_adapter.py
"""Databricks SQL adapter integration tests.

Skipped unless DQT_DATABRICKS_HTTP_PATH env var is set.
Enable job via GitHub Actions var DQT_DATABRICKS_ENABLED=true.

Required env vars:
  DQT_DATABRICKS_HOST         — e.g. adb-123456789.1.azuredatabricks.net
  DQT_DATABRICKS_TOKEN        — personal access token or service principal token
  DQT_DATABRICKS_HTTP_PATH    — /sql/1.0/warehouses/<warehouse-id>
  DQT_DATABRICKS_CATALOG      — Unity Catalog name (optional, defaults to hive_metastore)
"""
import os
import pytest

pytestmark = pytest.mark.adapter


def _require_env(name: str) -> str:
    val = os.environ.get(name, "")
    if not val:
        pytest.skip(f"{name} not set — skipping Databricks tests")
    return val


@pytest.fixture(scope="module")
def adapter():
    from dqt.adapters.databricks import DatabricksAdapter
    return DatabricksAdapter(
        host=_require_env("DQT_DATABRICKS_HOST"),
        token=_require_env("DQT_DATABRICKS_TOKEN"),
        http_path=_require_env("DQT_DATABRICKS_HTTP_PATH"),
        catalog=os.environ.get("DQT_DATABRICKS_CATALOG", "hive_metastore"),
    )


def test_health_check(adapter):
    result = adapter.health_check()
    assert result.ok, f"Databricks health check failed: {result}"


def test_list_schemas(adapter):
    schemas = adapter.list_schemas()
    assert isinstance(schemas, list)
    assert len(schemas) > 0


def test_list_tables(adapter):
    schemas = adapter.list_schemas()
    for schema in schemas:
        tables = adapter.list_tables(schema)
        if tables:
            assert isinstance(tables, list)
            return
    pytest.skip("No tables found in any schema")


def test_describe_columns(adapter):
    schemas = adapter.list_schemas()
    for schema in schemas:
        tables = adapter.list_tables(schema)
        if tables:
            cols = adapter.describe_columns(schema, tables[0])
            assert len(cols) > 0
            return
    pytest.skip("No tables found")


def test_sample(adapter):
    schemas = adapter.list_schemas()
    for schema in schemas:
        tables = adapter.list_tables(schema)
        if tables:
            df = adapter.sample(schema, tables[0], n=10)
            assert len(df) <= 10
            return
    pytest.skip("No tables found")


def test_read_only_enforced(adapter):
    """Adapter connection must not allow writes."""
    import pytest
    with pytest.raises(Exception):
        # Any write attempt must raise
        adapter._execute_write("CREATE TABLE dqt_test_write_guard (x INT)")
