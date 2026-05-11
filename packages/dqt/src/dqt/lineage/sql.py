"""SQL file ingestion for table-level lineage via sqlglot AST walking.
Ref: https://sqlglot.com/sqlglot/expressions.html
"""
from __future__ import annotations

import logging
from pathlib import Path

from dqt.lineage.models import LineageEdge, LineageGraph, LineageNode

logger = logging.getLogger(__name__)


def _qualified(table) -> str:
    """Return a stable dotted name for a sqlglot Table expression.

    Uses sqlglot string properties (.catalog, .db, .name) which always return
    plain strings, avoiding the TypeError caused by raw Identifier nodes.
    """
    parts = [p for p in (table.catalog, table.db, table.name) if p]
    return ".".join(parts) if parts else str(table)


def from_sql_files(paths: list[str | Path]) -> LineageGraph:
    """Parse CREATE TABLE/VIEW statements from SQL files and return a LineageGraph.

    sqlglot must be installed (``pip install 'dqtlib[lineage]'``).

    Example::

        graph = from_sql_files(["models/orders.sql", "models/sessions.sql"])
        print(len(graph.nodes), "tables")
        print(len(graph.edges), "lineage edges")
    """
    try:
        import sqlglot
        import sqlglot.expressions as exp
    except ImportError as exc:
        raise ImportError(
            "sqlglot is required for SQL lineage parsing. "
            "Install it with: pip install 'dqtlib[lineage]'"
        ) from exc

    graph = LineageGraph()
    seen_tables: set[str] = set()

    def _ensure_node(name: str) -> None:
        if name not in seen_tables:
            seen_tables.add(name)
            graph.add_node(LineageNode(id=name, kind="dataset", label=name, dataset=name))

    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            logger.warning("sql lineage: file not found, skipping: %s", path)
            continue

        sql = path.read_text(encoding="utf-8")
        try:
            statements = sqlglot.parse(sql)
        except Exception:
            logger.warning("sql lineage: parse error, skipping: %s", path, exc_info=True)
            continue

        for statement in statements:
            if statement is None:
                continue

            # Identify CREATE TABLE … AS SELECT or CREATE VIEW … AS SELECT
            if not isinstance(statement, (exp.Create,)):
                continue

            # The target table/view name
            this = statement.args.get("this")
            if this is None:
                continue

            target_name: str | None = None
            if isinstance(this, (exp.Table, exp.Schema)):
                target_name = _qualified(this) if isinstance(this, exp.Table) else this.name
            if not target_name:
                continue

            _ensure_node(target_name)

            # Walk the SELECT body for source table references
            expression = statement.args.get("expression")
            if expression is None:
                continue

            for table in expression.find_all(exp.Table):
                src_name = _qualified(table)
                if not src_name or src_name == target_name:
                    continue
                _ensure_node(src_name)
                graph.add_edge(
                    LineageEdge(
                        source=src_name,
                        target=target_name,
                        kind="column_lineage",
                        confidence=0.9,
                    )
                )

    return graph
