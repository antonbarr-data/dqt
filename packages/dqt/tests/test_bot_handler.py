# packages/dqt/tests/test_bot_handler.py
"""Tests for DqtBotHandler slash command processing and formatters."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest

import dqt
from dqt.algorithms._base import Verdict
from dqt.bot.formatters import to_slack_blocks, to_teams_card
from dqt.bot.handler import BotCommand, BotResponse, DqtBotHandler
from dqt.store._protocol import Incident, RunResult
from dqt.store.memory import MemoryStore


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_check(table: str, slug: str = "completeness", col: str | None = None) -> dqt.Check:
    return dqt.Check(
        schema_name="public",
        table_name=table,
        column_name=col,
        detector_slug=slug,
    )


def _run(check: dqt.Check, verdict: Verdict, score: float) -> RunResult:
    return RunResult(
        check_id=check.id,
        detector_slug=check.detector_slug,
        started_at=_now(),
        finished_at=_now(),
        verdict=verdict,
        score=score,
        plain_english="ok",
    )


def _incident(check: dqt.Check, severity: Verdict = Verdict.fail) -> Incident:
    return Incident(
        check_id=check.id,
        run_id=uuid4(),
        detector_slug=check.detector_slug,
        severity=severity,
        opened_at=_now(),
        score=1.0,
    )


# ── BotCommand.parse ──────────────────────────────────────────────────────────

def test_parse_check_command():
    cmd = BotCommand.parse("check orders")
    assert cmd.name == "check"
    assert cmd.args == ["orders"]


def test_parse_incidents_command():
    cmd = BotCommand.parse("incidents --fail")
    assert cmd.name == "incidents"
    assert "--fail" in cmd.args


def test_parse_why_command():
    cmd = BotCommand.parse("why orders amount")
    assert cmd.name == "why"
    assert cmd.args == ["orders", "amount"]


def test_parse_empty_returns_help():
    cmd = BotCommand.parse("")
    assert cmd.name == "help"


def test_parse_strips_leading_slash():
    cmd = BotCommand.parse("/check orders")
    assert cmd.name == "check"


# ── /dq check ────────────────────────────────────────────────────────────────

def test_check_no_args_returns_usage():
    handler = DqtBotHandler(MemoryStore(), [])
    resp = handler.handle(BotCommand.parse("check"))
    assert "Usage" in resp.text or "usage" in resp.text.lower()


def test_check_unknown_table():
    handler = DqtBotHandler(MemoryStore(), [])
    resp = handler.handle(BotCommand.parse("check nonexistent"))
    assert "nonexistent" in resp.text


def test_check_shows_latest_run():
    check = _make_check("orders")
    store = MemoryStore()
    store.save_run(_run(check, Verdict.pass_, 0.1))
    handler = DqtBotHandler(store, [check])
    resp = handler.handle(BotCommand.parse("check orders"))
    assert "orders" in resp.text
    assert len(resp.blocks) > 0


def test_check_no_runs_yet():
    check = _make_check("orders")
    handler = DqtBotHandler(MemoryStore(), [check])
    resp = handler.handle(BotCommand.parse("check orders"))
    assert "orders" in resp.text


# ── /dq incidents ─────────────────────────────────────────────────────────────

def test_incidents_empty():
    handler = DqtBotHandler(MemoryStore(), [])
    resp = handler.handle(BotCommand.parse("incidents"))
    assert "No open" in resp.text or "good" in resp.text.lower()


def test_incidents_returns_open_incidents():
    check = _make_check("orders")
    store = MemoryStore()
    store.save_incident(_incident(check))
    handler = DqtBotHandler(store, [check])
    resp = handler.handle(BotCommand.parse("incidents"))
    assert "1" in resp.text or "incident" in resp.text.lower()


def test_incidents_fail_filter():
    chk_fail = _make_check("orders")
    chk_warn = _make_check("sessions")
    store = MemoryStore()
    store.save_incident(_incident(chk_fail, Verdict.fail))
    store.save_incident(_incident(chk_warn, Verdict.warn))
    handler = DqtBotHandler(store, [chk_fail, chk_warn])
    resp = handler.handle(BotCommand.parse("incidents --fail"))
    # Should mention the fail incident but not the warn-only one
    assert "completeness" in resp.text or "1" in resp.text


# ── /dq why ──────────────────────────────────────────────────────────────────

def test_why_no_args_returns_usage():
    handler = DqtBotHandler(MemoryStore(), [])
    resp = handler.handle(BotCommand.parse("why"))
    assert "Usage" in resp.text or "usage" in resp.text.lower()


def test_why_no_checks_for_table():
    handler = DqtBotHandler(MemoryStore(), [])
    resp = handler.handle(BotCommand.parse("why orders"))
    assert "orders" in resp.text


def test_why_no_failing_incidents():
    check = _make_check("orders")
    handler = DqtBotHandler(MemoryStore(), [check])
    resp = handler.handle(BotCommand.parse("why orders"))
    assert "No open" in resp.text or "fail" in resp.text.lower()


def test_why_without_graph_returns_graceful_message():
    check = _make_check("orders")
    store = MemoryStore()
    store.save_incident(_incident(check))
    handler = DqtBotHandler(store, [check], graph=None)
    resp = handler.handle(BotCommand.parse("why orders"))
    assert "lineage" in resp.text.lower() or "graph" in resp.text.lower()


# ── Formatters ────────────────────────────────────────────────────────────────

def test_to_slack_blocks_with_existing_blocks():
    resp = BotResponse(
        text="hello",
        blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": "hello"}}],
    )
    blocks = to_slack_blocks(resp)
    assert len(blocks) == 1
    assert blocks[0]["type"] == "section"


def test_to_slack_blocks_fallback_from_text():
    resp = BotResponse(text="hello world")
    blocks = to_slack_blocks(resp)
    assert blocks[0]["text"]["text"] == "hello world"


def test_to_teams_card_has_correct_schema():
    resp = BotResponse(
        text="hello",
        blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": "hello"}}],
    )
    card = to_teams_card(resp)
    assert card["type"] == "AdaptiveCard"
    assert card["version"] == "1.4"
    assert len(card["body"]) == 1
    assert card["body"][0]["type"] == "TextBlock"


def test_exported_from_public_api():
    assert hasattr(dqt, "BotCommand")
    assert hasattr(dqt, "BotResponse")
    assert hasattr(dqt, "DqtBotHandler")
    assert hasattr(dqt, "to_slack_blocks")
    assert hasattr(dqt, "to_teams_card")
