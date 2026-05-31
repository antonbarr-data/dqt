from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

import pandas as pd


@dataclass
class AggExpr:
    name: str
    sql: str


@dataclass
class HealthCheckStep:
    name: str
    status: Literal["pass", "fail", "skip"]
    latency_ms: float
    detail: str


@dataclass
class HealthCheckResult:
    steps: list[HealthCheckStep] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(s.status in ("pass", "skip") for s in self.steps)


@dataclass
class ColumnMeta:
    name: str
    data_type: str
    nullable: bool
    position: int


@dataclass
class ColumnProfileResult:
    column: str = ""
    kind: str = "unknown"
    data_type: str | None = None
    nullable: bool | None = None
    position: int | None = None
    total_count: int | None = None
    null_count: int | None = None
    zero_count: int | None = None
    empty_count: int | None = None
    distinct_count: int | None = None
    p_min: float | None = None
    p_max: float | None = None
    p_mean: float | None = None
    p_stddev: float | None = None
    p2: float | None = None
    p5: float | None = None
    p10: float | None = None
    p25: float | None = None
    p50: float | None = None
    p75: float | None = None
    p90: float | None = None
    p95: float | None = None
    p98: float | None = None
    p99: float | None = None
    histogram: list | None = None
    top_values: list | None = None


@runtime_checkable
class WarehouseAdapter(Protocol):
    sql_dialect: str  # "bigquery" | "postgres" | "clickhouse" | "duckdb" | "ansi"

    def health_check(self) -> HealthCheckResult: ...
    def sample(self, schema: str, table: str, n: int = 100_000, where: str | None = None) -> pd.DataFrame: ...
    def aggregate(self, schema: str, table: str, exprs: list[AggExpr]) -> dict[str, object]: ...
    def describe_columns(self, schema: str, table: str) -> list[ColumnMeta]: ...
    def list_schemas(self) -> list[str]: ...
    def list_tables(self, schema: str) -> list[str]: ...
    def profile_column(self, schema: str, table: str, column: str) -> ColumnProfileResult: ...
