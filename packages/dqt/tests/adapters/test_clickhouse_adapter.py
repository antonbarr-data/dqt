# packages/dqt/tests/adapters/test_clickhouse_adapter.py
"""ClickHouse adapter integration tests — runs via testcontainers, no credentials needed."""
import pytest

pytestmark = pytest.mark.adapter

CLICKHOUSE_IMAGE = "clickhouse/clickhouse-server:24"


@pytest.fixture(scope="module")
def ch_url():
    """Start a ClickHouse container and return a connection URL."""
    try:
        from testcontainers.clickhouse import ClickHouseContainer
    except ImportError:
        pytest.skip("testcontainers[clickhouse] not installed")
    with ClickHouseContainer(CLICKHOUSE_IMAGE) as ch:
        yield ch.get_connection_url()


@pytest.fixture(scope="module")
def adapter(ch_url):
    from dqt.adapters.clickhouse import ClickHouseAdapter
    return ClickHouseAdapter(dsn=ch_url)


@pytest.fixture(scope="module")
def seeded(ch_url):
    """Seed a test table."""
    try:
        import clickhouse_driver
    except ImportError:
        pytest.skip("clickhouse-driver not installed")
    client = clickhouse_driver.Client.from_url(ch_url)
    client.execute(
        "CREATE TABLE IF NOT EXISTS dqt_test.orders "
        "(id UInt32, amount Float64, status String) ENGINE = Memory"
    )
    client.execute(
        "INSERT INTO dqt_test.orders VALUES",
        [{"id": i, "amount": float(i), "status": "active" if i % 2 == 0 else ""}
         for i in range(200)],
    )
    yield
    client.execute("DROP TABLE IF EXISTS dqt_test.orders")


def test_health_check(adapter):
    result = adapter.health_check()
    assert result.ok, f"ClickHouse health check failed: {result}"


def test_list_schemas(adapter, seeded):
    schemas = adapter.list_schemas()
    assert isinstance(schemas, list)
    assert "dqt_test" in schemas


def test_list_tables(adapter, seeded):
    tables = adapter.list_tables("dqt_test")
    assert "orders" in tables


def test_describe_columns(adapter, seeded):
    cols = adapter.describe_columns("dqt_test", "orders")
    names = [c.name for c in cols]
    assert "amount" in names
    assert "status" in names


def test_sample(adapter, seeded):
    df = adapter.sample("dqt_test", "orders", n=50)
    assert len(df) <= 200
    assert "amount" in df.columns


def test_aggregate_null_fraction(adapter, seeded):
    from dqt.adapters._protocol import AggExpr
    result = adapter.aggregate(
        "dqt_test", "orders",
        [AggExpr(name="null_count", expr="countIf(amount IS NULL)"),
         AggExpr(name="total_count", expr="count()")]
    )
    assert "null_count" in result
    assert "total_count" in result
    assert result["total_count"] == 200
