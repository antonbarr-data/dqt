"""Convert SuiteResult to a Slack Block Kit payload."""
from __future__ import annotations

from typing import Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from dqt.runner.runner import SuiteResult

# Controls which individual check rows appear in the message.
# "all"  — pass + warn + fail
# "warn" — warn + fail only (default)
# "fail" — fail only
ReportLevel = Literal["all", "warn", "fail"]

_EMOJI = {"pass": ":white_check_mark:", "warn": ":warning:", "fail": ":red_circle:"}
_LEVEL_VERDICTS: dict[ReportLevel, set[str]] = {
    "all":  {"pass", "warn", "fail"},
    "warn": {"warn", "fail"},
    "fail": {"fail"},
}


def suite_to_slack_blocks(
    suite: SuiteResult,
    *,
    title: str = "dqt check suite",
    level: ReportLevel = "warn",
) -> list[dict]:
    """Build Slack Block Kit blocks from a SuiteResult.

    Args:
        suite: result from Runner.run_suite()
        title: message header text
        level: minimum verdict to include in per-check rows.
               "all" shows every check, "warn" shows warn+fail (default),
               "fail" shows only failures.
    """
    passed = [r for r in suite.ran if r.verdict.value == "pass"]
    warned  = [r for r in suite.ran if r.verdict.value == "warn"]
    failed  = [r for r in suite.ran if r.verdict.value == "fail"]

    summary_parts = [
        f":white_check_mark: {len(passed)} passed",
        f":warning: {len(warned)} warned",
        f":red_circle: {len(failed)} failed",
    ]
    if suite.skipped:
        summary_parts.append(f"{len(suite.skipped)} skipped")

    blocks: list[dict] = [
        {"type": "header", "text": {"type": "plain_text", "text": title, "emoji": True}},
        {"type": "section", "text": {"type": "mrkdwn", "text": "  ·  ".join(summary_parts)}},
        {"type": "divider"},
    ]

    show = _LEVEL_VERDICTS[level]
    # Always show worst first: fail → warn → pass
    ordered = failed + warned + passed
    visible = [r for r in ordered if r.verdict.value in show]

    for r in visible:
        emoji = _EMOJI[r.verdict.value]
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{emoji} *{r.detector_slug}*  `score={r.score:.3f}`\n{r.plain_english}",
            },
        })

    if suite.skipped:
        skipped_text = "\n".join(
            f"• `{c.detector_slug}` on {c.schema_name}.{c.table_name} — {reason}"
            for c, reason in suite.skipped
        )
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Skipped*\n{skipped_text}"},
        })

    footer_parts = [
        f"budget spent: ${suite.budget_spent_usd:.4f} / ${suite.budget_total_usd:.4f}",
        f"showing: {level}+",
    ]
    blocks.append({"type": "context", "elements": [
        {"type": "mrkdwn", "text": "  ·  ".join(footer_parts)},
    ]})

    return blocks
