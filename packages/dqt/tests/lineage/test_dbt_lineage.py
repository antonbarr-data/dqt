import json
import pathlib
import sys
import unittest.mock

import pytest


def _write_manifest(tmp_path: pathlib.Path, manifest: dict) -> pathlib.Path:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest))
    return p


@pytest.mark.unit
def test_column_level_edges_extracted(tmp_path):
    """from_dbt_manifest should produce column-kind LineageNodes when compiled_code is present."""
    from dqt.lineage.dbt import from_dbt_manifest

    manifest = {
        "nodes": {
            "model.proj.orders": {
                "resource_type": "model",
                "name": "orders",
                "unique_id": "model.proj.orders",
                "depends_on": {"nodes": ["source.proj.raw.raw_orders"]},
                "compiled_code": (
                    "SELECT id, amount, customer_id FROM raw.raw_orders"
                ),
                "columns": {
                    "id": {"name": "id"},
                    "amount": {"name": "amount"},
                    "customer_id": {"name": "customer_id"},
                },
            }
        },
        "sources": {
            "source.proj.raw.raw_orders": {
                "resource_type": "source",
                "name": "raw_orders",
                "unique_id": "source.proj.raw.raw_orders",
                "depends_on": {"nodes": []},
                "columns": {
                    "id": {"name": "id"},
                    "amount": {"name": "amount"},
                    "customer_id": {"name": "customer_id"},
                },
            }
        },
    }
    p = _write_manifest(tmp_path, manifest)
    graph = from_dbt_manifest(p)

    column_nodes = [n for n in graph.nodes if n.kind == "column"]
    assert len(column_nodes) > 0, "Expected column-level nodes"

    column_edges = [e for e in graph.edges if e.kind == "column_derived_from"]
    assert len(column_edges) > 0, "Expected column-level edges"

    amount_edge = next(
        (e for e in column_edges if "amount" in e.target and "orders" in e.target),
        None,
    )
    assert amount_edge is not None, "Expected column edge for 'amount'"


@pytest.mark.unit
def test_table_level_edges_still_present(tmp_path):
    """Table-level derived_from edges must still be produced alongside column edges."""
    from dqt.lineage.dbt import from_dbt_manifest

    manifest = {
        "nodes": {
            "model.proj.orders": {
                "resource_type": "model",
                "name": "orders",
                "unique_id": "model.proj.orders",
                "depends_on": {"nodes": ["source.proj.raw.raw_orders"]},
                "compiled_code": "SELECT id FROM raw.raw_orders",
                "columns": {"id": {"name": "id"}},
            }
        },
        "sources": {
            "source.proj.raw.raw_orders": {
                "resource_type": "source",
                "name": "raw_orders",
                "unique_id": "source.proj.raw.raw_orders",
                "depends_on": {"nodes": []},
                "columns": {"id": {"name": "id"}},
            }
        },
    }
    p = _write_manifest(tmp_path, manifest)
    graph = from_dbt_manifest(p)

    table_edges = [e for e in graph.edges if e.kind == "derived_from"]
    assert len(table_edges) > 0, "Expected table-level derived_from edges"


@pytest.mark.unit
def test_no_compiled_sql_degrades_to_table_level(tmp_path):
    """Models without compiled_code produce only table-level edges, not column edges."""
    from dqt.lineage.dbt import from_dbt_manifest

    manifest = {
        "nodes": {
            "model.proj.orders": {
                "resource_type": "model",
                "name": "orders",
                "unique_id": "model.proj.orders",
                "depends_on": {"nodes": ["source.proj.raw.raw_orders"]},
                "columns": {"id": {"name": "id"}},
                # no compiled_code
            }
        },
        "sources": {
            "source.proj.raw.raw_orders": {
                "resource_type": "source",
                "name": "raw_orders",
                "unique_id": "source.proj.raw.raw_orders",
                "depends_on": {"nodes": []},
                "columns": {"id": {"name": "id"}},
            }
        },
    }
    p = _write_manifest(tmp_path, manifest)
    graph = from_dbt_manifest(p)

    column_edges = [e for e in graph.edges if e.kind == "column_derived_from"]
    assert len(column_edges) == 0, "No column edges expected without compiled SQL"

    table_edges = [e for e in graph.edges if e.kind == "derived_from"]
    assert len(table_edges) == 1, "One table-level edge expected"


@pytest.mark.unit
def test_sqlglot_import_error_degrades_to_table_level(tmp_path):
    """When sqlglot.lineage is unavailable, column edges are silently skipped."""
    from dqt.lineage.dbt import from_dbt_manifest

    manifest = {
        "nodes": {
            "model.proj.orders": {
                "resource_type": "model",
                "name": "orders",
                "unique_id": "model.proj.orders",
                "depends_on": {"nodes": ["source.proj.raw.raw_orders"]},
                "compiled_code": "SELECT id, amount FROM raw.raw_orders",
                "columns": {"id": {"name": "id"}, "amount": {"name": "amount"}},
            }
        },
        "sources": {
            "source.proj.raw.raw_orders": {
                "resource_type": "source",
                "name": "raw_orders",
                "unique_id": "source.proj.raw.raw_orders",
                "depends_on": {"nodes": []},
                "columns": {"id": {"name": "id"}, "amount": {"name": "amount"}},
            }
        },
    }
    p = _write_manifest(tmp_path, manifest)

    with unittest.mock.patch.dict(sys.modules, {"sqlglot.lineage": None}):
        import importlib
        import dqt.lineage.dbt as dbt_module
        importlib.reload(dbt_module)
        graph = dbt_module.from_dbt_manifest(p)

    column_edges = [e for e in graph.edges if e.kind == "column_derived_from"]
    assert len(column_edges) == 0, "No column edges expected when sqlglot.lineage absent"

    table_edges = [e for e in graph.edges if e.kind == "derived_from"]
    assert len(table_edges) == 1, "Table-level edge must still be produced"


@pytest.mark.unit
def test_multiple_upstream_tables(tmp_path):
    """Column edges are produced correctly when a model joins two sources."""
    from dqt.lineage.dbt import from_dbt_manifest

    manifest = {
        "nodes": {
            "model.proj.enriched": {
                "resource_type": "model",
                "name": "enriched",
                "unique_id": "model.proj.enriched",
                "depends_on": {"nodes": [
                    "source.proj.raw.orders",
                    "source.proj.raw.customers",
                ]},
                "compiled_code": (
                    "SELECT o.id, o.amount, c.name "
                    "FROM raw.orders o JOIN raw.customers c ON o.customer_id = c.id"
                ),
                "columns": {
                    "id": {"name": "id"},
                    "amount": {"name": "amount"},
                    "name": {"name": "name"},
                },
            }
        },
        "sources": {
            "source.proj.raw.orders": {
                "resource_type": "source",
                "name": "orders",
                "unique_id": "source.proj.raw.orders",
                "depends_on": {"nodes": []},
                "columns": {
                    "id": {"name": "id"},
                    "amount": {"name": "amount"},
                    "customer_id": {"name": "customer_id"},
                },
            },
            "source.proj.raw.customers": {
                "resource_type": "source",
                "name": "customers",
                "unique_id": "source.proj.raw.customers",
                "depends_on": {"nodes": []},
                "columns": {
                    "id": {"name": "id"},
                    "name": {"name": "name"},
                },
            },
        },
    }
    p = _write_manifest(tmp_path, manifest)
    graph = from_dbt_manifest(p)

    column_edges = [e for e in graph.edges if e.kind == "column_derived_from"]
    assert len(column_edges) > 0, "Expected column edges for join model"

    amount_edge = next(
        (e for e in column_edges if "amount" in e.target),
        None,
    )
    assert amount_edge is not None, "Expected column edge for 'amount'"
    assert "orders" in amount_edge.source, f"Expected source from orders, got {amount_edge.source!r}"
