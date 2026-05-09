from __future__ import annotations

from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class BaselineConfig(BaseModel):
    window_days: int = 14
    min_rows: int = 1_000


class CheckScope(BaseModel):
    """Controls which rows are included when the check runs."""

    mode: Literal["entire", "incremental", "custom"] = "entire"
    key_col: str | None = None  # column to compare against `since` (incremental)
    since: str | None = None  # ISO datetime string or "last_run"; incremental only
    custom_sql: str | None = None  # WHERE clause fragment; custom only


class CheckFilter(BaseModel):
    """Row-level equality filter applied before sampling."""

    col: str
    values: list[Any]  # one or more allowed values (OR'd together)


class Check(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    schema_name: str
    table_name: str
    column_name: str | None = None
    detector_slug: str
    params: dict[str, Any] = Field(default_factory=dict)
    baseline: BaselineConfig | None = None
    schedule: str | None = None
    sample_n: int = 100_000
    sampling_pct: float | None = None  # 0–100; overrides sample_n if set
    scope: CheckScope | None = None
    filters: list[CheckFilter] = Field(default_factory=list)
