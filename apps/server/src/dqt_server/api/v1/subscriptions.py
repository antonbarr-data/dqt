"""Subscription CRUD API -- GET/POST/PUT/DELETE + preview endpoint."""
from __future__ import annotations

from datetime import datetime, time, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from dqt.subscriptions.models import Cadence, DeliveryChannel, Subscription
from dqt.subscriptions.store import SubscriptionStore

router = APIRouter(prefix="/api/v1/subscriptions", tags=["subscriptions"])

_store = SubscriptionStore()


class SubscriptionCreate(BaseModel):
    user_id: str
    metric_fqns: list[str]
    cadence: Cadence
    delivery_channels: list[DeliveryChannel]
    significance_threshold: float | None = None
    schedule_hour: int = 8


class SubscriptionUpdate(BaseModel):
    metric_fqns: list[str] | None = None
    cadence: Cadence | None = None
    delivery_channels: list[DeliveryChannel] | None = None
    significance_threshold: float | None = None
    schedule_hour: int | None = None


def _to_dict(sub: Subscription) -> dict:
    return {
        "id": str(sub.id),
        "user_id": sub.user_id,
        "metric_fqns": sub.metric_fqns,
        "cadence": sub.cadence,
        "delivery_channels": sub.delivery_channels,
        "significance_threshold": sub.significance_threshold,
        "schedule_time": sub.schedule_time.strftime("%H:%M"),
        "created_at": sub.created_at.isoformat(),
    }


@router.get("")
async def list_subscriptions(user_id: str = "demo") -> list[dict]:
    return [_to_dict(s) for s in _store.list_for_user(user_id)]


@router.post("")
async def create_subscription(body: SubscriptionCreate) -> dict:
    sub = Subscription(
        user_id=body.user_id,
        metric_fqns=body.metric_fqns,
        cadence=body.cadence,
        delivery_channels=body.delivery_channels,
        significance_threshold=body.significance_threshold,
        schedule_time=time(body.schedule_hour, 0),
        created_at=datetime.now(timezone.utc),
    )
    _store.save(sub)
    return _to_dict(sub)


@router.put("/{sub_id}")
async def update_subscription(sub_id: str, body: SubscriptionUpdate) -> dict:
    sub = _store.get(UUID(sub_id))
    if sub is None:
        raise HTTPException(status_code=404, detail=f"Subscription {sub_id} not found")
    if body.metric_fqns is not None:
        sub.metric_fqns = body.metric_fqns
    if body.cadence is not None:
        sub.cadence = body.cadence
    if body.delivery_channels is not None:
        sub.delivery_channels = body.delivery_channels
    if body.significance_threshold is not None:
        sub.significance_threshold = body.significance_threshold
    if body.schedule_hour is not None:
        sub.schedule_time = time(body.schedule_hour, 0)
    _store.update(sub)
    return _to_dict(sub)


@router.delete("/{sub_id}")
async def delete_subscription(sub_id: str) -> dict:
    if not _store.delete(UUID(sub_id)):
        raise HTTPException(status_code=404, detail=f"Subscription {sub_id} not found")
    return {"id": sub_id, "deleted": True}


@router.get("/{sub_id}/preview")
async def preview_subscription(sub_id: str) -> dict:
    from dqt_server.api.v1.insights import _get_registry
    from dqt.store.memory import MemoryStore
    from dqt.insights.digest import generate_daily

    sub = _store.get(UUID(sub_id))
    if sub is None:
        raise HTTPException(status_code=404, detail=f"Subscription {sub_id} not found")

    registry = _get_registry()
    catalog = [
        {"fqn": m.fqn, "display_name": m.display_name}
        for m in registry.list()
        if m.fqn in sub.metric_fqns
    ]
    digest = generate_daily(catalog, MemoryStore())
    return {
        "subscription_id": sub_id,
        "cadence": sub.cadence,
        "plain_text": digest.to_plain_text(),
        "html": digest.to_html(),
        "data_issues_count": len(digest.data_issues),
        "real_shifts_count": len(digest.real_shifts),
        "no_significant_change_count": len(digest.no_significant_change),
    }
