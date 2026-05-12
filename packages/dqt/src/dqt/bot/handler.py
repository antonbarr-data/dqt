# packages/dqt/src/dqt/bot/handler.py
"""Slash-command bot handler for dqt.

/dq check <table>           — most recent run result for all checks on <table>
/dq incidents [--fail]      — open incidents (optionally filtered to fail severity)
/dq why <table> [<column>]  — causal explanation for the latest failing incident

Zero server dependency: takes a Runner, ResultsStore, and optionally a
LineageGraph as constructor args. Formatting (Slack blocks, Teams card)
is in formatters.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dqt.lineage.models import LineageGraph
    from dqt.runner.runner import Runner
    from dqt.store._protocol import ResultsStore


@dataclass
class BotCommand:
    """Parsed /dq slash command."""
    name: str          # "check" | "incidents" | "why"
    args: list[str] = field(default_factory=list)
    user_id: str = ""
    workspace_id: str = ""

    @staticmethod
    def parse(text: str, user_id: str = "", workspace_id: str = "") -> "BotCommand":
        """Parse '/dq check orders' -> BotCommand(name='check', args=['orders'])."""
        parts = text.strip().split()
        if not parts:
            return BotCommand(name="help", args=[], user_id=user_id, workspace_id=workspace_id)
        name = parts[0].lstrip("/")
        return BotCommand(name=name, args=parts[1:], user_id=user_id, workspace_id=workspace_id)


@dataclass
class BotResponse:
    """Platform-agnostic bot response."""
    text: str
    blocks: list[dict[str, Any]] = field(default_factory=list)   # Slack block-kit JSON
    card: dict[str, Any] = field(default_factory=dict)            # Teams adaptive card JSON


class DqtBotHandler:
    """Processes /dq slash commands using the library's runtime objects.

    Args:
        store: ResultsStore holding RunResult and Incident records.
        checks: list of Check objects the bot can reference.
        runner: Optional Runner (used to trigger on-demand runs in future).
        graph: Optional LineageGraph (used by 'why' command for causal explanation).
    """

    def __init__(
        self,
        store: "ResultsStore",
        checks: list,
        runner: "Runner | None" = None,
        graph: "LineageGraph | None" = None,
    ) -> None:
        self._store = store
        self._checks = checks
        self._runner = runner
        self._graph = graph

    def handle(self, command: BotCommand) -> BotResponse:
        dispatch = {
            "check": self._handle_check,
            "incidents": self._handle_incidents,
            "why": self._handle_why,
        }
        handler = dispatch.get(command.name)
        if handler is None:
            return self._handle_help()
        return handler(command.args)

    # ------------------------------------------------------------------
    # /dq check <table>
    # ------------------------------------------------------------------

    def _handle_check(self, args: list[str]) -> BotResponse:
        if not args:
            return BotResponse(
                text="Usage: /dq check <table_name>",
                blocks=[_section("Usage: `/dq check <table_name>`")],
            )
        table_name = args[0]
        matching = [c for c in self._checks if c.table_name == table_name]
        if not matching:
            return BotResponse(
                text=f"No checks found for table `{table_name}`.",
                blocks=[_section(f"No checks found for table `{table_name}`.")],
            )

        rows: list[str] = []
        for check in matching:
            runs = self._store.list_runs(check.id, limit=1)
            if runs:
                r = runs[0]
                verdict_emoji = {"pass": "ok_hand", "warn": "warning", "fail": "x"}.get(r.verdict.value, "question")
                col_part = f"`.{check.column_name}`" if check.column_name else ""
                rows.append(
                    f":{verdict_emoji}: `{check.detector_slug}`{col_part} — "
                    f"score {r.score:.3f} ({r.verdict.value})"
                )
            else:
                col_part = f"`.{check.column_name}`" if check.column_name else ""
                rows.append(f":grey_question: `{check.detector_slug}`{col_part} — no runs yet")

        text_body = "\n".join(rows)
        summary = f"*{table_name}* — {len(matching)} check(s)\n{text_body}"
        return BotResponse(
            text=f"{table_name}: {len(matching)} checks — {text_body}",
            blocks=[_section(summary)],
        )

    # ------------------------------------------------------------------
    # /dq incidents [--fail]
    # ------------------------------------------------------------------

    def _handle_incidents(self, args: list[str]) -> BotResponse:
        from dqt.algorithms._base import Verdict
        fail_only = "--fail" in args
        incidents = self._store.list_all_incidents()
        open_incs = [i for i in incidents if i.status == "open"]
        if fail_only:
            open_incs = [i for i in open_incs if i.severity == Verdict.fail]

        if not open_incs:
            severity_label = " (fail)" if fail_only else ""
            text = f"No open incidents{severity_label}. Everything looks good."
            return BotResponse(text=text, blocks=[_section(f":white_check_mark: {text}")])

        rows: list[str] = []
        for inc in open_incs[:10]:  # cap at 10 to avoid message overflow
            emoji = ":x:" if inc.severity.value == "fail" else ":warning:"
            rows.append(f"{emoji} `{inc.detector_slug}` — score {inc.score:.3f}")
        overflow = f"\n_...and {len(open_incs) - 10} more_" if len(open_incs) > 10 else ""

        text_body = "\n".join(rows) + overflow
        summary = f"*{len(open_incs)} open incident(s)*\n{text_body}"
        return BotResponse(
            text=f"{len(open_incs)} open incidents: {', '.join(i.detector_slug for i in open_incs[:5])}",
            blocks=[_section(summary)],
        )

    # ------------------------------------------------------------------
    # /dq why <table> [<column>]
    # ------------------------------------------------------------------

    def _handle_why(self, args: list[str]) -> BotResponse:
        if not args:
            return BotResponse(
                text="Usage: /dq why <table_name> [<column_name>]",
                blocks=[_section("Usage: `/dq why <table_name> [<column_name>]`")],
            )
        table_name = args[0]
        column_name = args[1] if len(args) > 1 else None

        # Find the most recent failing incident for a check on this table/column
        matching_checks = [
            c for c in self._checks
            if c.table_name == table_name
            and (column_name is None or c.column_name == column_name)
        ]
        if not matching_checks:
            return BotResponse(
                text=f"No checks found for `{table_name}`.",
                blocks=[_section(f"No checks found for `{table_name}`.")],
            )

        from dqt.algorithms._base import Verdict
        all_incidents = self._store.list_all_incidents()
        relevant_ids = {c.id for c in matching_checks}
        failing = [
            i for i in all_incidents
            if i.check_id in relevant_ids and i.severity == Verdict.fail and i.status == "open"
        ]
        if not failing:
            return BotResponse(
                text=f"No open fail incidents for `{table_name}`.",
                blocks=[_section(f":white_check_mark: No open fail incidents for `{table_name}`.")],
            )

        incident = failing[-1]  # most recent

        if self._graph is None:
            return BotResponse(
                text=f"Incident on `{incident.detector_slug}` — no lineage graph available for causal explanation.",
                blocks=[_section(
                    f":warning: Incident on `{incident.detector_slug}` (score {incident.score:.3f})\n"
                    "_No lineage graph configured — attach a LineageGraph to enable causal explanation._"
                )],
            )

        from dqt.lineage.explain import explain_incident
        explanation = explain_incident(incident, self._checks, self._store, self._graph)

        if explanation is None:
            return BotResponse(
                text="Could not explain: check not resolved in lineage graph.",
                blocks=[_section(":grey_question: Could not resolve check in lineage graph.")],
            )

        strong = [e for e in explanation.causes if e.evidence_strength in ("strong", "moderate")]
        if strong:
            top = strong[0]
            detail = (
                f":mag: *{explanation.plain_english}*\n"
                f"Upstream node: `{top.upstream_node_id}` "
                f"(lag={top.selected_lag}, adj p={top.granger_adjusted_p:.4f})"
            )
        else:
            detail = f":grey_question: {explanation.plain_english}"

        return BotResponse(
            text=explanation.plain_english,
            blocks=[_section(detail)],
        )

    # ------------------------------------------------------------------
    # Help
    # ------------------------------------------------------------------

    def _handle_help(self) -> BotResponse:
        help_text = (
            "*dqt slash commands*\n"
            "• `/dq check <table>` — latest check results for a table\n"
            "• `/dq incidents [--fail]` — list open incidents\n"
            "• `/dq why <table> [<column>]` — causal explanation for latest failure"
        )
        return BotResponse(text=help_text, blocks=[_section(help_text)])


# ──────────────────────────────────────────────────────────────────────────────
# Internal block builders
# ──────────────────────────────────────────────────────────────────────────────

def _section(text: str) -> dict[str, Any]:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}
