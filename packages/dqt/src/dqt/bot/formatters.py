# packages/dqt/src/dqt/bot/formatters.py
"""Platform-specific formatters for BotResponse.

to_slack_blocks: returns the blocks list directly (already block-kit JSON)
to_teams_card: wraps blocks in a Teams Adaptive Card body
"""
from __future__ import annotations

from typing import Any

from dqt.bot.handler import BotResponse


def to_slack_blocks(response: BotResponse) -> list[dict[str, Any]]:
    """Return Slack block-kit payload for the response.

    If blocks are already present, return them. Otherwise wrap text as a section.
    """
    if response.blocks:
        return response.blocks
    return [{"type": "section", "text": {"type": "mrkdwn", "text": response.text}}]


def to_teams_card(response: BotResponse) -> dict[str, Any]:
    """Return a minimal Teams Adaptive Card for the response.

    Produces a version 1.4 card with one TextBlock per Slack section block.
    When a pre-built card is present on the response, it is returned as-is.
    """
    if response.card:
        return response.card

    body: list[dict[str, Any]] = []
    for block in response.blocks:
        if block.get("type") == "section":
            text_obj = block.get("text", {})
            raw = text_obj.get("text", "")
            body.append({
                "type": "TextBlock",
                "text": raw,
                "wrap": True,
            })

    if not body:
        body.append({"type": "TextBlock", "text": response.text, "wrap": True})

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": body,
    }
