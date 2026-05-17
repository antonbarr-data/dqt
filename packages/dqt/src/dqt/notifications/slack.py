"""Slack notifier -- sends Block Kit payloads to an Incoming Webhook URL.

Configure via SLACK_WEBHOOK_URL env var or pass webhook_url directly.
No Bot token required.
"""
from __future__ import annotations

import json
import os
import urllib.request


class SlackNotifier:
    def __init__(self, webhook_url: str | None = None) -> None:
        self.webhook_url = webhook_url if webhook_url is not None else os.environ.get("SLACK_WEBHOOK_URL", "")

    def send_blocks(self, blocks: list[dict], *, text: str = "dqt notification") -> bool:
        """Post Block Kit blocks to the webhook. Returns True on success."""
        if not self.webhook_url:
            return False
        payload = json.dumps({"text": text, "blocks": blocks}).encode()
        req = urllib.request.Request(
            self.webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception:
            return False

    def send_text(self, text: str) -> bool:
        """Post a plain text message to the webhook."""
        return self.send_blocks([], text=text)
