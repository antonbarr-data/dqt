import pytest

pytestmark = pytest.mark.adapter


@pytest.fixture(scope="module")
def pg_url():
    """Provide a live Postgres URL via testcontainers."""
    from testcontainers.postgres import PostgresContainer
    import sqlalchemy
    with PostgresContainer("postgres:16") as pg:
        engine = sqlalchemy.create_engine(pg.get_connection_url())
        with engine.begin() as conn:
            conn.execute(sqlalchemy.text("CREATE SCHEMA IF NOT EXISTS test_schema"))
            conn.execute(sqlalchemy.text("""
                CREATE TABLE IF NOT EXISTS test_schema.orders (
                    id serial PRIMARY KEY,
                    amount numeric,
                    status text
                )
            """))
            for i in range(100):
                conn.execute(sqlalchemy.text(
                    "INSERT INTO test_schema.orders (amount, status) VALUES (:a, :s)"
                ), {"a": float(i), "s": "active" if i % 2 == 0 else None})
        yield pg.get_connection_url()


@pytest.fixture(scope="module")
def adapter(pg_url):
    from dqt.adapters.postgres import PostgresAdapter
    return PostgresAdapter(conn_str=pg_url)


def test_health_check_passes(adapter):
    result = adapter.health_check()
    assert result.passed, [s for s in result.steps if s.status not in ("pass", "skip")]


def test_health_check_has_six_steps(adapter):
    result = adapter.health_check()
    assert len(result.steps) == 6
    names = [s.name for s in result.steps]
    assert names == ["tcp_reach", "auth", "info_schema", "sample_select", "latency_probe", "clock_skew"]


def test_list_schemas(adapter):
    schemas = adapter.list_schemas()
    assert "test_schema" in schemas


def test_list_tables(adapter):
    tables = adapter.list_tables("test_schema")
    assert "orders" in tables


def test_describe_columns(adapter):
    cols = adapter.describe_columns("test_schema", "orders")
    names = [c.name for c in cols]
    assert "id" in names
    assert "amount" in names


def test_sample(adapter):
    df = adapter.sample("test_schema", "orders", n=50)
    assert len(df) == 50
    assert "amount" in df.columns


def test_aggregate(adapter):
    from dqt.adapters._protocol import AggExpr
    result = adapter.aggregate("test_schema", "orders", [
        AggExpr(name="total", sql="COUNT(*)"),
        AggExpr(name="null_status", sql="SUM(CASE WHEN status IS NULL THEN 1 ELSE 0 END)"),
    ])
    assert result["total"] == 100
    assert result["null_status"] == 50
