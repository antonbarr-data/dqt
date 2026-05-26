"""Trigger API -- on-demand digest delivery with history."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/trigger", tags=["trigger"])

_digest_log: list[dict] = []  # in-memory digest history


class TriggerRequest(BaseModel):
    mode: Literal["daily", "weekly"] = "daily"
    slack_webhook_url: str | None = None
    smtp_host: str | None = None
    dry_run: bool = False


@router.post("")
async def run_trigger(body: TriggerRequest) -> dict:
    from dqt_server.api.v1.insights import _get_registry
    from dqt.store.memory import MemoryStore
    from dqt.notifications.slack import SlackNotifier
    from dqt.notifications.email import EmailNotifier
    from dqt.insights.digest import generate_daily, generate_weekly

    registry = _get_registry()
    catalog = [{"fqn": m.fqn, "display_name": m.display_name} for m in registry.list()]
    store = MemoryStore()

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
    result: dict = {"mode": body.mode, "dry_run": body.dry_run, **entry}

    if not body.dry_run:
        if body.slack_webhook_url:
            SlackNotifier(webhook_url=body.slack_webhook_url).send_blocks(
                digest.to_slack_blocks(), text=f"dqt {body.mode.capitalize()} Digest"
            )
        if body.smtp_host:
            EmailNotifier(host=body.smtp_host).send(
                "team", f"dqt {body.mode.capitalize()} Digest", digest.to_html(), digest.to_plain_text()
            )

    return result


@router.get("/history")
async def trigger_history() -> list[dict]:
    return _digest_log
