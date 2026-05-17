from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from typing import Literal
from uuid import UUID, uuid4

Cadence = Literal["daily", "weekly", "on_threshold"]
DeliveryChannel = Literal["slack", "email"]


@dataclass
class Subscription:
    user_id: str
    metric_fqns: list[str]
    cadence: Cadence
    delivery_channels: list[DeliveryChannel]
    significance_threshold: float | None = None  # None = use per-metric 2σ default
    schedule_time: time = field(default_factory=lambda: time(8, 0))  # 08:00 UTC
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: UUID = field(default_factory=uuid4)
