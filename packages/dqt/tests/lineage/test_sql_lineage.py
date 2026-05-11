from dqt.lineage.sql import from_sql_files


def test_schema_qualified_table_does_not_crash(tmp_path):
    """Regression: stg.stg_payments raised TypeError before this fix."""
    p = tmp_path / "qualified.sql"
    p.write_text("""
    CREATE VIEW analytics.orders AS
    SELECT o.id, p.amount
    FROM stg.stg_orders AS o
    JOIN stg.stg_payments AS p ON o.id = p.order_id;
    """)
    graph = from_sql_files([p])
    node_ids = {n.id for n in graph.nodes}
    assert "analytics.orders" in node_ids
    assert "stg.stg_orders" in node_ids
    assert "stg.stg_payments" in node_ids


def test_three_part_name(tmp_path):
    """catalog.schema.table should parse correctly."""
    p = tmp_path / "three_part.sql"
    p.write_text("CREATE VIEW my_db.dbo.v_orders AS SELECT * FROM my_db.raw.orders;")
    graph = from_sql_files([p])
    node_ids = {n.id for n in graph.nodes}
    assert "my_db.dbo.v_orders" in node_ids
    assert "my_db.raw.orders" in node_ids


def test_bare_table_name(tmp_path):
    """Unqualified table names still work."""
    p = tmp_path / "bare.sql"
    p.write_text("CREATE VIEW v_orders AS SELECT * FROM orders;")
    graph = from_sql_files([p])
    assert any(n.id == "v_orders" for n in graph.nodes)
    assert any(n.id == "orders" for n in graph.nodes)
