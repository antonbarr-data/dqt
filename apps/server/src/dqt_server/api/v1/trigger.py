"""Trigger API -- on-demand threshold check and digest delivery with history."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/trigger", tags=["trigger"])

_digest_log: list[dict] = []  # in-memory digest history for M4


class TriggerRequest(BaseModel):
    mode: Literal["threshold", "daily", "weekly"] = "threshold"
    slack_webhook_url: str | None = None
    smtp_host: str | None = None
    dry_run: bool = False


@router.post("")
async def run_trigger(body: TriggerRequest) -> dict:
    from dqt_server.api.v1.insights import _get_registry
    from dqt_server.api.v1.subscriptions import _store as sub_store
    from dqt.store.memory import MemoryStore
    from dqt.notifications.slack import SlackNotifier
    from dqt.notifications.email import EmailNotifier

    registry = _get_registry()
    catalog = [{"fqn": m.fqn, "display_name": m.display_name} for m in registry.list()]
    store = MemoryStore()

    notifiers: list = []
    if not body.dry_run:
        if body.slack_webhook_url:
            notifiers.append(SlackNotifier(webhook_url=body.slack_webhook_url))
        if body.smtp_host:
            notifiers.append(EmailNotifier(host=body.smtp_host))

    result: dict = {"mode": body.mode, "dry_run": body.dry_run}

    if body.mode == "threshold":
        from dqt.insights.trigger import check_thresholds
        summary = check_thresholds(catalog, store, sub_store, notifiers)
        result.update(summary)
        return result

    from dqt.insights.digest import generate_daily, generate_weekly
    digest = generate_daily(catalog, store) if body.mode == "daily" else generate_weekly(catalog, store)

    entry = {
        "cadence": digest.cadence,
        "generated_at": digest.generated_at.isoformat(),
        "data_issues_count": len(digest.data_issues),
        "real_shifts_count": len(digest.real_shifts),
        "no_significant_change_count": len(digest.no_significant_change),
        "plain_text": digest.to_plain_text(),
    }
    _digest_log.append(entry)
    result.update(entry)

    if not body.dry_run:
        all_user_ids = {s.user_id for m in catalog for s in sub_store.list_for_metric(m["fqn"])}
        for user_id in all_user_ids:
            user_subs = [s for s in sub_store.list_for_user(user_id) if s.cadence == body.mode]
            if not user_subs:
                continue
            sub = user_subs[0]
            for notifier in notifiers:
                ntype = type(notifier).__name__
                if ntype == "SlackNotifier" and "slack" in sub.delivery_channels:
                    notifier.send_blocks(digest.to_slack_blocks(), text=f"dqt {body.mode.capitalize()} Digest")
                elif ntype == "EmailNotifier" and "email" in sub.delivery_channels:
                    notifier.send(user_id, f"dqt {body.mode.capitalize()} Digest", digest.to_html(), digest.to_plain_text())

    return result


@router.get("/history")
async def digest_history() -> list[dict]:
    return list(reversed(_digest_log))
