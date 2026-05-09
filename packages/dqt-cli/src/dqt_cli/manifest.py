from __future__ import annotations

from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


class ColumnSemantic(BaseModel):
    name: str
    description: str = ""
    classification: str = "internal"
    unit: str = ""
    pii: bool = False


class TableSemantic(BaseModel):
    model_config = {"populate_by_name": True}

    schema_name: str = Field("public", alias="schema")
    name: str
    description: str = ""
    columns: list[ColumnSemantic] = Field(default_factory=list)


class SemanticLayer(BaseModel):
    tables: list[TableSemantic] = Field(default_factory=list)


class SourceConfig(BaseModel):
    type: Literal["duckdb", "csv", "parquet", "postgres"]
    id: str = "default"
    # duckdb
    database: str = ":memory:"
    # csv/parquet
    path: str = ""
    table_name: str = ""
    # postgres
    connection_string: str = ""


class Manifest(BaseModel):
    version: str = "1"
    source: SourceConfig
    semantic: SemanticLayer = Field(default_factory=SemanticLayer)
    checks: list[dict[str, Any]] = Field(default_factory=list)


def load_manifest(path: str) -> Manifest:
    with open(path) as f:
        raw = yaml.safe_load(f)
    return Manifest.model_validate(raw)
