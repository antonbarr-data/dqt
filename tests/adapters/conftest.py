"""Shared fixtures and skip helpers for live adapter tests."""
import os
import pytest


def _skip_unless(*env_vars: str, adapter: str):
    missing = [v for v in env_vars if not os.environ.get(v)]
    if missing:
        pytest.skip(f"{adapter} credentials not set: {missing}")


@pytest.fixture(scope="module")
def skip_no_clickhouse():
    _skip_unless("CLICKHOUSE_HOST", "CLICKHOUSE_USER", "CLICKHOUSE_PASSWORD", adapter="ClickHouse")


@pytest.fixture(scope="module")
def skip_no_snowflake():
    _skip_unless(
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_USER",
        "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_WAREHOUSE",
        adapter="Snowflake",
    )


@pytest.fixture(scope="module")
def skip_no_bigquery():
    _skip_unless("GCP_SA_KEY_BIGQUERY", "GCP_PROJECT_ID", adapter="BigQuery")


@pytest.fixture(scope="module")
def skip_no_databricks():
    _skip_unless(
        "DATABRICKS_HOST",
        "DATABRICKS_TOKEN",
        "DATABRICKS_HTTP_PATH",
        adapter="Databricks",
    )
