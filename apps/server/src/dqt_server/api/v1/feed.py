"""Feed API -- Today feed and weekly view built from real check-run history."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from dqt.insights.feed import FeedItem, rank
from dqt_server.db.engine import get_db
from dqt_server.models.gigler import CheckRun, MetricDefinition

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


async def _build_feed_items(db: AsyncSession, lookback_hours: int) -> list[FeedItem]:
    metric_rows = await db.execute(select(MetricDefinition))
    metrics = metric_rows.scalars().all()
    if not metrics:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    items: list[FeedItem] = []

    for metric in metrics:
        runs_q = await db.execute(
            select(CheckRun)
            .where(CheckRun.dataset_id == metric.dataset, CheckRun.ran_at >= cutoff)
            .order_by(desc(CheckRun.ran_at))
            .limit(100)
        )
        runs = runs_q.scalars().all()

        if not runs:
            continue

        fail_count = sum(1 for r in runs if r.verdict == "fail")
        warn_count = sum(1 for r in runs if r.verdict == "warn")
        total = len(runs)

        if fail_count > 0:
            significance = min(0.85 + (fail_count / total) * 0.15, 1.0)
        elif warn_count > 0:
            significance = 0.45 + (warn_count / total) * 0.35
        else:
            significance = max(0.05, 0.20 - total * 0.001)

        scores = [r.score for r in runs if r.score is not None]
        if len(scores) >= 2:
            denom = max(abs(scores[-1]), 0.001)
            observed_change = max(-1.0, min(1.0, (scores[0] - scores[-1]) / denom))
        else:
            observed_change = 0.0

        worst = "fail" if fail_count > 0 else "warn" if warn_count > 0 else "pass"
        direction = "fell" if observed_change < 0 else "rose"
        summary = (
            f"{metric.display_name} score {direction} "
            f"{abs(observed_change) * 100:.1f}% — "
            f"{fail_count} failing, {warn_count} warning checks across {total} runs."
        )

        items.append(FeedItem(
            metric_fqn=metric.fqn,
            display_name=metric.display_name,
            observed_change=observed_change,
            significance=significance,
            executive_tier="finance" in (metric.tags or []),
            novelty=significance,
            engagement=0.0,
            summary_paragraph=summary,
            primary_channel="data",
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
async def feed_today(
    lookback: str = "24h",
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    hours = 24
    if lookback.endswith("h"):
        hours = int(lookback[:-1])
    elif lookback.endswith("d"):
        hours = int(lookback[:-1]) * 24

    items = await _build_feed_items(db, lookback_hours=hours)
    ranked = rank(items, window=timedelta(hours=hours), limit=limit)
    return [_item_to_dict(i) for i in ranked if i.item_id not in _reviewed]


@router.get("/weekly")
async def feed_weekly(
    week: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    items = await _build_feed_items(db, lookback_hours=168)
    ranked = rank(items, window=timedelta(hours=168), limit=50)
    return [_item_to_dict(i) for i in ranked]


@router.post("/items/{item_id}/reviewed")
async def mark_reviewed(item_id: str) -> dict:
    _reviewed.add(item_id)
    _save_reviewed(_reviewed)
    return {"item_id": item_id, "reviewed": True}
