from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class BaselineConfig(BaseModel):
    window_days: int = 14
    min_rows: int = 1_000


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
