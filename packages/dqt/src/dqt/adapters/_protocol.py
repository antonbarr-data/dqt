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


@runtime_checkable
class WarehouseAdapter(Protocol):
    def health_check(self) -> HealthCheckResult: ...
    def sample(self, schema: str, table: str, n: int = 100_000) -> pd.DataFrame: ...
    def aggregate(self, schema: str, table: str, exprs: list[AggExpr]) -> dict[str, object]: ...
    def describe_columns(self, schema: str, table: str) -> list[ColumnMeta]: ...
    def list_schemas(self) -> list[str]: ...
    def list_tables(self, schema: str) -> list[str]: ...
