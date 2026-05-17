from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

MetricKind = Literal["ratio", "count", "sum", "model"]


@dataclass
class Metric:
    fqn: str                     # fully-qualified: source.schema.table.metric_name
    display_name: str
    kind: MetricKind
    dataset: str                 # dataset id this metric is derived from
    description: str
    owners: list[str]
    tags: list[str]
    unit: str = ""
    warn_threshold: float | None = None
    fail_threshold: float | None = None
    current_value: float | None = None
    current_verdict: str | None = None
    last_run: str | None = None
