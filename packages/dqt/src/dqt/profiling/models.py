from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class NumericStats:
    mean: float
    std: float
    min: float
    q25: float
    median: float
    q75: float
    max: float


@dataclass
class StringStats:
    min_length: int
    avg_length: float
    median_length: float
    max_length: int


@dataclass
class DateStats:
    min: str  # ISO format
    max: str
    date_range_days: int


@dataclass
class BoolStats:
    true_count: int
    false_count: int
    true_pct: float


@dataclass
class TopValue:
    value: str
    count: int
    pct: float


@dataclass
class HistogramBin:
    left: float
    right: float
    count: int


@dataclass
class ColumnProfile:
    name: str
    data_type: str
    null_count: int
    null_pct: float
    distinct_count: int
    unique_pct: float
    total_count: int
    distribution_type: str
    numeric_stats: NumericStats | None = None
    string_stats: StringStats | None = None
    date_stats: DateStats | None = None
    bool_stats: BoolStats | None = None
    histogram: list[HistogramBin] = field(default_factory=list)
    top_values: list[TopValue] = field(default_factory=list)


@dataclass
class DatasetProfile:
    schema_name: str
    table_name: str
    row_count: int
    column_count: int
    columns: list[ColumnProfile]
    profiled_at: str  # ISO 8601
    sample_n: int
    filters_applied: dict[str, tuple] | None = None
