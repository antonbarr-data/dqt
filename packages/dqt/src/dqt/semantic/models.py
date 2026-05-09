from __future__ import annotations
from pydantic import BaseModel, Field


class ColumnDescription(BaseModel):
    name: str
    description: str = ""
    classification: str = "internal"
    pii: bool = False
    unit: str = ""
    tags: list[str] = Field(default_factory=list)


class DatasetDescription(BaseModel):
    id: str
    description: str = ""
    owner: str = ""
    domain: str = ""
    freshness_sla_hours: float | None = None
    source_files: list[str] = Field(default_factory=list)
    columns: list[ColumnDescription] = Field(default_factory=list)


class SemanticManifest(BaseModel):
    version: str = "1"
    datasets: list[DatasetDescription] = Field(default_factory=list)

    def get_dataset(self, id: str) -> DatasetDescription | None:
        return next((d for d in self.datasets if d.id == id), None)

    def get_column(self, dataset_id: str, column_name: str) -> ColumnDescription | None:
        ds = self.get_dataset(dataset_id)
        if ds is None:
            return None
        return next((c for c in ds.columns if c.name == column_name), None)
