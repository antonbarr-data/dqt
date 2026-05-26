# Ref: https://duckdb.org/docs/api/python/overview — used for SQL aggregations on DataFrames
from __future__ import annotations

import pathlib
import time
from typing import Any

import pandas as pd

from dqt.adapters._protocol import (
    AggExpr,
    ColumnMeta,
    HealthCheckResult,
    HealthCheckStep,
)
from dqt.utils.logging import get_logger

_log = get_logger(__name__)

_READERS: dict[str, Any] = {
    ".csv":     lambda p: pd.read_csv(p),
    ".tsv":     lambda p: pd.read_csv(p, sep="\t"),
    ".xlsx":    lambda p: pd.read_excel(p),
    ".xls":     lambda p: pd.read_excel(p),
    ".parquet": lambda p: pd.read_parquet(p),
    ".json":    lambda p: pd.read_json(p),
    ".jsonl":   lambda p: pd.read_json(p, lines=True),
    ".ndjson":  lambda p: pd.read_json(p, lines=True),
    ".feather": lambda p: pd.read_feather(p),
    ".arrow":   lambda p: pd.read_feather(p),
}

_HEALTH_STEPS = ("readable", "parseable", "columns", "sample_read", "row_count")


class LocalFileAdapter:
    """Reads a local file and exposes it as a single-table WarehouseAdapter."""
    sql_dialect = "duckdb"

    def __init__(self, path: str | pathlib.Path) -> None:
        self._path = pathlib.Path(path)
        self._suffix = self._path.suffix.lower()
        if self._suffix not in _READERS:
            supported = ", ".join(sorted(_READERS))
            raise ValueError(f"Unsupported format '{self._suffix}'. Supported: {supported}")
        self._table_name = self._path.stem

    def _read(self) -> pd.DataFrame:
        return _READERS[self._suffix](self._path)

    def health_check(self) -> HealthCheckResult:
        steps: list[HealthCheckStep] = []

        t0 = time.perf_counter()
        if not self._path.exists():
            steps.append(HealthCheckStep("file_exists", "fail", 0.0, f"not found: {self._path}"))
            for name in _HEALTH_STEPS:
                steps.append(HealthCheckStep(name, "skip", 0.0, "skipped"))
            return HealthCheckResult(steps=steps)
        steps.append(HealthCheckStep("file_exists", "pass", (time.perf_counter() - t0) * 1000, str(self._path)))

        t0 = time.perf_counter()
        try:
            self._path.read_bytes()[:1024]
            steps.append(HealthCheckStep("readable", "pass", (time.perf_counter() - t0) * 1000, "ok"))
        except Exception as exc:
            steps.append(HealthCheckStep("readable", "fail", 0.0, str(exc)))
            for name in ("parseable", "columns", "sample_read", "row_count"):
                steps.append(HealthCheckStep(name, "skip", 0.0, "skipped"))
            return HealthCheckResult(steps=steps)

        t0 = time.perf_counter()
        try:
            df = self._read()
        except Exception as exc:
            steps.append(HealthCheckStep("parseable", "fail", 0.0, str(exc)))
            for name in ("columns", "sample_read", "row_count"):
                steps.append(HealthCheckStep(name, "skip", 0.0, "skipped"))
            return HealthCheckResult(steps=steps)
        steps.append(HealthCheckStep("parseable", "pass", (time.perf_counter() - t0) * 1000, f"{len(df.columns)} columns"))

        steps.append(HealthCheckStep("columns", "pass", 0.0, str(list(df.columns)[:5])))
        steps.append(HealthCheckStep("sample_read", "pass", 0.0, "ok"))
        steps.append(HealthCheckStep("row_count", "pass", 0.0, f"{len(df)} rows"))
        return HealthCheckResult(steps=steps)

    def list_schemas(self) -> list[str]:
        return ["default"]

    def list_tables(self, schema: str) -> list[str]:
        return [self._table_name]

    def describe_columns(self, schema: str, table: str) -> list[ColumnMeta]:
        df = self._read()
        return [
            ColumnMeta(
                name=col,
                data_type=str(df[col].dtype),
                nullable=bool(df[col].isna().any()),
                position=i + 1,
            )
            for i, col in enumerate(df.columns)
        ]

    def sample(self, schema: str, table: str, n: int = 100_000, where: str | None = None) -> pd.DataFrame:
        df = self._read()
        if len(df) <= n:
            return df.reset_index(drop=True)
        return df.sample(n=n, random_state=42).reset_index(drop=True)

    def aggregate(self, schema: str, table: str, exprs: list[AggExpr]) -> dict[str, Any]:
        import duckdb
        df = self._read()
        con = duckdb.connect()
        con.register("_data", df)
        cols = ", ".join(f"{e.sql} AS {e.name}" for e in exprs)
        row = con.execute(f"SELECT {cols} FROM _data").fetchone()  # noqa: S608
        con.close()
        return dict(zip([e.name for e in exprs], row))
