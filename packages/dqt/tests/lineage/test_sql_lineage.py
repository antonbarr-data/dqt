import pytest


def test_schema_qualified_table_does_not_crash():
    """Regression: stg.stg_payments raised TypeError before this fix."""
    import tempfile
    import pathlib
    from dqt.lineage.sql import from_sql_files

    sql = """
    CREATE VIEW analytics.orders AS
    SELECT o.id, p.amount
    FROM stg.stg_orders AS o
    JOIN stg.stg_payments AS p ON o.id = p.order_id;
    """
    with tempfile.NamedTemporaryFile(suffix=".sql", mode="w", delete=False) as f:
        f.write(sql)
        path = f.name
    graph = from_sql_files([path])
    node_ids = {n.id for n in graph.nodes}
    assert "analytics.orders" in node_ids
    assert "stg.stg_orders" in node_ids
    assert "stg.stg_payments" in node_ids


def test_three_part_name():
    """catalog.schema.table should parse correctly."""
    import tempfile
    from dqt.lineage.sql import from_sql_files

    sql = "CREATE VIEW my_db.dbo.v_orders AS SELECT * FROM my_db.raw.orders;"
    with tempfile.NamedTemporaryFile(suffix=".sql", mode="w", delete=False) as f:
        f.write(sql)
        path = f.name
    graph = from_sql_files([path])
    node_ids = {n.id for n in graph.nodes}
    assert "my_db.dbo.v_orders" in node_ids
    assert "my_db.raw.orders" in node_ids


def test_bare_table_name():
    """Unqualified table names still work."""
    import tempfile
    from dqt.lineage.sql import from_sql_files

    sql = "CREATE VIEW v_orders AS SELECT * FROM orders;"
    with tempfile.NamedTemporaryFile(suffix=".sql", mode="w", delete=False) as f:
        f.write(sql)
        path = f.name
    graph = from_sql_files([path])
    assert any(n.id == "v_orders" for n in graph.nodes)
    assert any(n.id == "orders" for n in graph.nodes)
