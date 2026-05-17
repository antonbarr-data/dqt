"""Batch narrative refresh -- runs nightly to pre-compute insights for every tracked metric.

Skips metrics with abs(observed_change) < min_change_threshold to avoid LLM cost burn.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from dqt.insights.explain import explain_movement
from dqt.store._protocol import ResultsStore


def refresh_all_narratives(
    metric_catalog: list[dict[str, Any]],
    store: ResultsStore,
    *,
    window: timedelta = timedelta(days=1),
    min_change_threshold: float = 0.02,
    use_llm: bool = True,
) -> dict[str, Any]:
    """Regenerate narratives for metrics with significant movement.

    Args:
        metric_catalog:        List of metric dicts with 'fqn' and 'display_name'.
        store:                 ResultsStore to query metric runs.
        window:                Time window for analysis (default 1 day).
        min_change_threshold:  Skip metrics with abs(change) < this (default 2%).
        use_llm:               Whether to use LLM for narrative generation.

    Returns:
        Summary dict: {"refreshed": int, "skipped": int}.
    """
    now = datetime.now(timezone.utc)
    window_start = now - window
    refreshed = 0
    skipped = 0

    for metric in metric_catalog:
        fqn = metric["fqn"]
        try:
            lookback_days = max(1, window.days + 7)
            runs = store.list_metric_runs(fqn, lookback_days=lookback_days)
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
        change = abs((last_val - first_val) / abs(first_val))
        if change < min_change_threshold:
            skipped += 1
            continue

        try:
            explain_movement(
                fqn,
                (window_start, now),
                store=store,
                use_llm=use_llm,
            )
            refreshed += 1
        except Exception:
            skipped += 1

    return {"refreshed": refreshed, "skipped": skipped}
