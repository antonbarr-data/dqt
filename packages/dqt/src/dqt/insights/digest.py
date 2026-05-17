"""Daily and weekly digest generation.

Groups subscribed metrics by primary_channel and produces Slack Block Kit,
HTML, and plain-text formatters for delivery.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from dqt.store._protocol import ResultsStore


@dataclass
class DigestEntry:
    metric_fqn: str
    display_name: str
    observed_change: float
    primary_channel: Literal["data", "business", "mixed"]
    summary_paragraph: str


@dataclass
class Digest:
    cadence: Literal["daily", "weekly"]
    generated_at: datetime
    data_issues: list[DigestEntry]
    real_shifts: list[DigestEntry]
    no_significant_change: list[DigestEntry]

    def to_plain_text(self) -> str:
        d = self.generated_at
        date_str = f"{d.year}-{d.month:02d}-{d.day:02d}"
        lines: list[str] = [
            f"dqt {self.cadence.capitalize()} Digest -- {date_str}",
            "=" * 50,
        ]
        if self.data_issues:
            lines.append("\nDATA ISSUES")
            for e in self.data_issues:
                lines.append(f"  {e.display_name} ({e.observed_change * 100:+.1f}%): {e.summary_paragraph}")
        if self.real_shifts:
            lines.append("\nREAL SHIFTS")
            for e in self.real_shifts:
                lines.append(f"  {e.display_name} ({e.observed_change * 100:+.1f}%): {e.summary_paragraph}")
        if self.no_significant_change:
            lines.append(f"\nNO SIGNIFICANT CHANGE ({len(self.no_significant_change)} metrics)")
        return "\n".join(lines)

    def to_slack_blocks(self, base_url: str = "http://localhost:3000") -> list[dict]:
        blocks: list[dict] = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f":bar_chart: dqt {self.cadence.capitalize()} Digest"},
            },
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"{self.generated_at.year}-{self.generated_at.month:02d}-{self.generated_at.day:02d}"}],
            },
            {"type": "divider"},
        ]
        for section_label, entries in [("Data Issues", self.data_issues), ("Real Shifts", self.real_shifts)]:
            if not entries:
                continue
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*{section_label}*"}})
            for e in entries:
                pct = f"{e.observed_change * 100:+.1f}%"
                url = f"{base_url}/metrics/{e.metric_fqn}"
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*<{url}|{e.display_name}>* {pct}\n{e.summary_paragraph}"},
                })
        if self.no_significant_change:
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"{len(self.no_significant_change)} subscribed metrics had no significant change."}],
            })
        return blocks

    def to_html(self, base_url: str = "http://localhost:3000") -> str:
        d = self.generated_at
        date_str = f"{d.year}-{d.month:02d}-{d.day:02d}"
        parts = [
            "<!DOCTYPE html><html><body style='font-family:sans-serif;max-width:600px;margin:auto'>",
            f"<h2>dqt {self.cadence.capitalize()} Digest</h2>",
            f"<p style='color:#888'>{date_str}</p>",
            "<hr>",
        ]
        for section_label, entries in [("Data Issues", self.data_issues), ("Real Shifts", self.real_shifts)]:
            if not entries:
                continue
            parts.append(f"<h3>{section_label}</h3>")
            for e in entries:
                pct = f"{e.observed_change * 100:+.1f}%"
                url = f"{base_url}/metrics/{e.metric_fqn}"
                parts.append(
                    f"<p><strong><a href='{url}'>{e.display_name}</a> {pct}</strong>"
                    f"<br>{e.summary_paragraph}</p>"
                )
        if self.no_significant_change:
            parts.append(
                f"<p style='color:#888'>{len(self.no_significant_change)} subscribed metrics had no significant change.</p>"
            )
        parts.append(
            "<hr><p style='color:#888;font-size:12px'>Sent by dqt -- "
            f"<a href='{base_url}/subscriptions'>manage subscriptions</a></p>"
            "</body></html>"
        )
        return "".join(parts)


def _build_digest(
    cadence: Literal["daily", "weekly"],
    metric_catalog: list[dict[str, Any]],
    store: ResultsStore,
    *,
    window: timedelta,
    significant_threshold: float = 0.02,
) -> Digest:
    now = datetime.now(timezone.utc)
    window_start = now - window
    data_issues: list[DigestEntry] = []
    real_shifts: list[DigestEntry] = []
    no_change: list[DigestEntry] = []

    for metric in metric_catalog:
        fqn = metric["fqn"]
        display_name = metric.get("display_name", fqn)
        try:
            runs = store.list_metric_runs(fqn, lookback_days=window.days + 30)
        except Exception:
            continue

        if len(runs) < 2:
            continue

        first_val = runs[0].value
        last_val = runs[-1].value
        change = (last_val - first_val) / abs(first_val) if first_val != 0 else 0.0

        if abs(change) < significant_threshold:
            no_change.append(DigestEntry(
                metric_fqn=fqn, display_name=display_name,
                observed_change=change, primary_channel="mixed",
                summary_paragraph="No significant change.",
            ))
            continue

        channel: Literal["data", "business", "mixed"] = "mixed"
        summary = (
            f"{display_name} {'fell' if change < 0 else 'rose'} "
            f"{abs(change) * 100:.1f}% in the {cadence} window."
        )
        try:
            from dqt.insights.explain import explain_movement
            expl = explain_movement(fqn, (window_start, now), store=store, use_llm=False)
            channel = expl.primary_channel
            summary = expl.summary_paragraph
        except Exception:
            pass

        entry = DigestEntry(
            metric_fqn=fqn, display_name=display_name,
            observed_change=change, primary_channel=channel, summary_paragraph=summary,
        )
        if channel == "data":
            data_issues.append(entry)
        else:
            real_shifts.append(entry)

    return Digest(
        cadence=cadence,
        generated_at=now,
        data_issues=data_issues,
        real_shifts=real_shifts,
        no_significant_change=no_change,
    )


def generate_daily(
    metric_catalog: list[dict[str, Any]],
    store: ResultsStore,
    *,
    significant_threshold: float = 0.02,
) -> Digest:
    """Generate a digest over the last 24 hours."""
    return _build_digest("daily", metric_catalog, store, window=timedelta(days=1), significant_threshold=significant_threshold)


def generate_weekly(
    metric_catalog: list[dict[str, Any]],
    store: ResultsStore,
    *,
    significant_threshold: float = 0.02,
) -> Digest:
    """Generate a digest over the last 7 days."""
    return _build_digest("weekly", metric_catalog, store, window=timedelta(days=7), significant_threshold=significant_threshold)
