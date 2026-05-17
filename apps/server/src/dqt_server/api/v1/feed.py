"""Feed API -- Today feed and weekly view."""
from __future__ import annotations

import json
import os
import random
from datetime import timedelta
from pathlib import Path

from fastapi import APIRouter

from dqt.insights.feed import FeedItem, rank

router = APIRouter(prefix="/api/v1/feed", tags=["feed"])

_REVIEWED_PATH = Path(os.environ.get("DQT_DATA_DIR", Path.home() / ".dqt")) / "feed_reviewed.json"


def _load_reviewed() -> set[str]:
    try:
        _REVIEWED_PATH.parent.mkdir(parents=True, exist_ok=True)
        if _REVIEWED_PATH.exists():
            return set(json.loads(_REVIEWED_PATH.read_text()))
    except Exception:
        pass
    return set()


def _save_reviewed(reviewed: set[str]) -> None:
    _REVIEWED_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REVIEWED_PATH.write_text(json.dumps(sorted(reviewed)))


_reviewed: set[str] = _load_reviewed()


def _synthetic_feed_items(lookback_hours: int = 24) -> list[FeedItem]:
    from dqt_server.api.v1.insights import _get_registry

    registry = _get_registry()
    items: list[FeedItem] = []
    rng = random.Random(42)

    for metric in registry.list():
        change = rng.uniform(-0.25, 0.25)
        sig = rng.uniform(0.4, 0.99)
        items.append(FeedItem(
            metric_fqn=metric.fqn,
            display_name=metric.display_name,
            observed_change=change,
            significance=sig,
            executive_tier="finance" in (metric.tags or []),
            novelty=rng.uniform(0.5, 1.0),
            engagement=rng.uniform(0.0, 2.0),
            summary_paragraph=(
                f"{metric.display_name} {'fell' if change < 0 else 'rose'} "
                f"{abs(change) * 100:.1f}% in the last {lookback_hours}h."
            ),
            primary_channel="mixed",
            estimated_data_contribution=(0.05, 0.20),
            estimated_business_contribution=(0.10, 0.35),
            evidence_chips=[],
        ))
    return items


def _item_to_dict(item: FeedItem) -> dict:
    return {
        "item_id": item.item_id,
        "metric_fqn": item.metric_fqn,
        "display_name": item.display_name,
        "observed_change": item.observed_change,
        "significance": item.significance,
        "primary_channel": item.primary_channel,
        "summary_paragraph": item.summary_paragraph,
        "estimated_data_contribution": list(item.estimated_data_contribution),
        "estimated_business_contribution": list(item.estimated_business_contribution),
        "evidence_chips": [
            {"label": c.label, "display_value": c.display_value, "direction": c.direction}
            for c in item.evidence_chips
        ],
        "reviewed": item.reviewed,
    }


@router.get("/today")
async def feed_today(lookback: str = "24h", limit: int = 20) -> list[dict]:
    hours = 24
    if lookback.endswith("h"):
        hours = int(lookback[:-1])
    elif lookback.endswith("d"):
        hours = int(lookback[:-1]) * 24

    items = _synthetic_feed_items(lookback_hours=hours)
    ranked = rank(items, window=timedelta(hours=hours), limit=limit)
    return [_item_to_dict(i) for i in ranked if i.item_id not in _reviewed]


@router.get("/weekly")
async def feed_weekly(week: str | None = None) -> list[dict]:
    items = _synthetic_feed_items(lookback_hours=168)
    ranked = rank(items, window=timedelta(hours=168), limit=50)
    return [_item_to_dict(i) for i in ranked]


@router.post("/items/{item_id}/reviewed")
async def mark_reviewed(item_id: str) -> dict:
    _reviewed.add(item_id)
    _save_reviewed(_reviewed)
    return {"item_id": item_id, "reviewed": True}
