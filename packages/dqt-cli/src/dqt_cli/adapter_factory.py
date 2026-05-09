from __future__ import annotations

import duckdb
import pandas as pd

from dqt_cli.manifest import SourceConfig


class CliDuckDBAdapter:
    """Minimal DuckDB-backed adapter for the CLI. Supports duckdb/csv/parquet sources."""

    def __init__(self, source: SourceConfig) -> None:
        if source.type == "postgres":
            raise NotImplementedError(
                "postgres source type is not supported in the CLI. "
                "Use the dqt server with a PostgreSQL warehouse connection."
            )
        if source.type == "duckdb":
            self._conn = duckdb.connect(source.database)
        else:
            # csv or parquet — load into in-memory DuckDB
            self._conn = duckdb.connect(":memory:")
            if source.type == "csv":
                tbl = source.table_name or "data"
                self._conn.execute(
                    f"CREATE TABLE {tbl} AS SELECT * FROM read_csv_auto('{source.path}')"
                )
            elif source.type == "parquet":
                tbl = source.table_name or "data"
                self._conn.execute(
                    f"CREATE TABLE {tbl} AS SELECT * FROM read_parquet('{source.path}')"
                )

    def sample(self, schema: str, table: str, n: int = 100_000, **kwargs) -> pd.DataFrame:
        full_name = f"{schema}.{table}" if schema and schema != "main" else table
        sampling_pct = kwargs.get("sampling_pct")
        if sampling_pct is not None:
            pct = max(0.001, min(100.0, float(sampling_pct)))
            sql = f"SELECT * FROM {full_name} USING SAMPLE {pct} PERCENT (bernoulli)"
        else:
            sql = f"SELECT * FROM {full_name} USING SAMPLE {n} ROWS"
        df = self._conn.execute(sql).fetchdf()
        # Apply CheckFilter equality filters
        for f in kwargs.get("filters", []):
            if f.col in df.columns:
                df = df[df[f.col].isin(f.values)]
        # Apply incremental scope
        scope = kwargs.get("scope")
        if scope and scope.mode == "incremental" and scope.key_col and scope.since:
            if scope.key_col in df.columns and scope.since != "last_run":
                try:
                    since_val = pd.to_datetime(scope.since)
                except (ValueError, TypeError):
                    since_val = scope.since
                df = df[df[scope.key_col] >= since_val]
        return df

    def aggregate(self, schema: str, table: str, exprs: list, **kwargs) -> dict:
        # Run each AggExpr against the table and return as a dict
        full_name = f"{schema}.{table}" if schema and schema != "main" else table
        selects = ", ".join(f"({e.sql}) AS {e.name}" for e in exprs)
        sql = f"SELECT {selects} FROM {full_name}"
        row = self._conn.execute(sql).fetchone()
        if row is None:
            return {e.name: None for e in exprs}
        return {e.name: v for e, v in zip(exprs, row)}

    def list_schemas(self) -> list[str]:
        return [
            row[0]
            for row in self._conn.execute(
                "SELECT schema_name FROM information_schema.schemata"
            ).fetchall()
        ]

    def list_tables(self, schema: str) -> list[str]:
        return [
            row[0]
            for row in self._conn.execute(
                f"SELECT table_name FROM information_schema.tables WHERE table_schema='{schema}'"
            ).fetchall()
        ]

    def describe_columns(self, schema: str, table: str) -> list:
        from dqt.adapters._protocol import ColumnMeta

        full = f"{schema}.{table}" if schema and schema != "main" else table
        rows = self._conn.execute(f"DESCRIBE {full}").fetchall()
        result = []
        for i, row in enumerate(rows):
            result.append(
                ColumnMeta(
                    name=row[0],
                    data_type=row[1],
                    nullable=(row[2] or "").upper() != "NOT NULL",
                    position=i,
                )
            )
        return result

    def health_check(self):
        from dqt.adapters._protocol import HealthCheckResult

        return HealthCheckResult(steps=[])


def build_adapter(source: SourceConfig) -> CliDuckDBAdapter:
    return CliDuckDBAdapter(source)
