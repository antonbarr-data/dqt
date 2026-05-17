"""Reactive threshold trigger.

Called by the batch scheduler or the trigger API endpoint. For each metric:
1. Fetches recent runs from the store
2. Computes current change vs per-metric significance threshold (or subscriber override)
3. When threshold crossed: runs explain_movement, identifies subscribers, fires notifications
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from dqt.insights.threshold import compute_threshold
from dqt.store._protocol import ResultsStore


def check_thresholds(
    metric_catalog: list[dict[str, Any]],
    store: ResultsStore,
    subscription_store: Any,  # SubscriptionStore -- Any avoids circular import
    notifiers: list[Any],     # list of SlackNotifier | EmailNotifier
    *,
    window: timedelta = timedelta(days=1),
    base_url: str = "http://localhost:3000",
) -> dict[str, Any]:
    """Check all metrics against significance thresholds and fire notifications.

    Returns summary dict: {triggered: int, skipped: int, notified: int}.
    """
    from dqt.insights.explain import explain_movement

    now = datetime.now(timezone.utc)
    window_start = now - window
    triggered = 0
    skipped = 0
    notified = 0

    for metric in metric_catalog:
        fqn = metric["fqn"]
        display_name = metric.get("display_name", fqn)

        try:
            runs = store.list_metric_runs(fqn, lookback_days=window.days + 30)
        except Exception:
            skipped += 1
            continue

        if len(runs) < 2:
            skipped += 1
            continue

        first_val = runs[0].value
        last_val = runs[-1].value
        if first_val == 0:
            skipped += 1
            continue
        change = (last_val - first_val) / abs(first_val)

        subscribers = subscription_store.list_for_metric(fqn)
        if not subscribers:
            skipped += 1
            continue

        default_threshold = compute_threshold(runs)
        relevant_subs = [
            s for s in subscribers
            if abs(change) >= (s.significance_threshold if s.significance_threshold is not None else default_threshold)
        ]
        if not relevant_subs:
            skipped += 1
            continue

        triggered += 1

        try:
            expl = explain_movement(fqn, (window_start, now), store=store, use_llm=False)
            summary = expl.summary_paragraph
        except Exception:
            direction = "fell" if change < 0 else "rose"
            summary = f"{display_name} {direction} {abs(change) * 100:.1f}% and crossed the significance threshold."

        pct = f"{change * 100:+.1f}%"
        metric_url = f"{base_url}/metrics/{fqn}"
        slack_blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": f":rotating_light: {display_name} {pct}"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": summary}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"<{metric_url}|View metric>"}},
        ]
        alert_text = f"dqt alert: {display_name} {pct}"

        for sub in relevant_subs:
            for notifier in notifiers:
                ntype = type(notifier).__name__
                try:
                    if ntype == "SlackNotifier" and "slack" in sub.delivery_channels:
                        notifier.send_blocks(slack_blocks, text=alert_text)
                        notified += 1
                    elif ntype == "EmailNotifier" and "email" in sub.delivery_channels:
                        notifier.send(
                            sub.user_id,
                            alert_text,
                            f"<p>{summary}</p><p><a href='{metric_url}'>View metric</a></p>",
                            f"{summary}\n\nView: {metric_url}",
                        )
                        notified += 1
                except Exception:
                    pass

    return {"triggered": triggered, "skipped": skipped, "notified": notified}
