# packages/dqt/tests/adapters/test_bigquery_adapter.py
"""BigQuery adapter integration tests.

Skipped unless DQT_BIGQUERY_PROJECT and GOOGLE_APPLICATION_CREDENTIALS env vars are set.
Enable job via GitHub Actions var DQT_BIGQUERY_ENABLED=true.
"""
import os
import pytest

pytestmark = pytest.mark.adapter


def _project() -> str:
    project = os.environ.get("DQT_BIGQUERY_PROJECT", "")
    if not project:
        pytest.skip("DQT_BIGQUERY_PROJECT not set — skipping BigQuery tests")
    return project


def _dataset() -> str:
    return os.environ.get("DQT_BIGQUERY_DATASET", "dqt_integration_test")


@pytest.fixture(scope="module")
def adapter():
    from dqt.adapters.bigquery import BigQueryAdapter
    return BigQueryAdapter(project=_project(), dataset=_dataset())


def test_health_check(adapter):
    result = adapter.health_check()
    assert result.ok, f"BigQuery health check failed: {result}"


def test_list_schemas(adapter):
    schemas = adapter.list_schemas()
    assert isinstance(schemas, list)
    assert _dataset() in schemas or len(schemas) > 0


def test_list_tables(adapter):
    tables = adapter.list_tables(_dataset())
    assert isinstance(tables, list)


def test_describe_columns(adapter):
    tables = adapter.list_tables(_dataset())
    if not tables:
        pytest.skip(f"No tables in dataset {_dataset()}")
    cols = adapter.describe_columns(_dataset(), tables[0])
    assert len(cols) > 0


def test_sample(adapter):
    tables = adapter.list_tables(_dataset())
    if not tables:
        pytest.skip(f"No tables in dataset {_dataset()}")
    df = adapter.sample(_dataset(), tables[0], n=10)
    assert len(df) <= 10


def test_dry_run_cost_guard(adapter):
    """BigQuery adapter must call dryRun before executing; refuse over-budget queries."""
    from dqt.adapters.bigquery import BigQueryAdapter
    frugal = BigQueryAdapter(project=_project(), dataset=_dataset(),
                             max_bytes_per_query=1)
    tables = adapter.list_tables(_dataset())
    if not tables:
        pytest.skip(f"No tables in dataset {_dataset()}")
    with pytest.raises(Exception, match="cost|bytes|budget|quota"):
        frugal.sample(_dataset(), tables[0], n=10_000)
