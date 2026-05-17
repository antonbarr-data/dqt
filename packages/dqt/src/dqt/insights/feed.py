"""Feed ranking -- produces a ranked list of FeedItem for the Today feed.

Ranking formula: score = magnitude * significance * executive_boost * novelty * (1 + engagement)
  - magnitude: abs(observed_change), clipped to [0, 1]
  - significance: statistical significance proxy, 0-1
  - executive_boost: 1.5 if executive_tier else 1.0
  - novelty: time-decay since last surfaced, 0-1 (caller provides)
  - engagement: click/view count proxy, 0-inf (small additive bonus)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Literal


@dataclass
class EvidenceChip:
    label: str
    display_value: str
    direction: Literal["up", "down", "flat"]


@dataclass
class FeedItem:
    metric_fqn: str
    display_name: str
    observed_change: float
    significance: float
    executive_tier: bool
    novelty: float
    engagement: float
    summary_paragraph: str
    primary_channel: Literal["data", "business", "mixed"]
    estimated_data_contribution: tuple[float, float]
    estimated_business_contribution: tuple[float, float]
    evidence_chips: list[EvidenceChip] = field(default_factory=list)
    reviewed: bool = False
    item_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])


def rank(items: list[FeedItem], *, window: timedelta, limit: int = 20) -> list[FeedItem]:
    """Return items sorted by importance score, truncated to limit."""
    # window reserved for M4 time-based novelty decay
    _ = window
    def score(item: FeedItem) -> float:
        magnitude = min(1.0, abs(item.observed_change))
        executive_boost = 1.5 if item.executive_tier else 1.0
        return magnitude * item.significance * executive_boost * item.novelty * (1.0 + item.engagement)

    return sorted(items, key=score, reverse=True)[:limit]
