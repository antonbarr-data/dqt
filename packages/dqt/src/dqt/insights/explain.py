"""explain_movement() -- the reconciliation orchestrator.

Combines Channel A (data integrity) and Channel B (business drivers) into a
single MovementExplanation, then calls the narrative pipeline to populate
summary_paragraph and citations.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

import pandas as pd

from dqt.insights.channel_a import scan as scan_channel_a
from dqt.insights.channel_b import analyze as analyze_channel_b, ChannelBReport
from dqt.insights.narrative import generate as generate_narrative, _apply_template
from dqt.insights.models import MovementExplanation
from dqt.store._protocol import ResultsStore


def explain_movement(
    metric_fqn: str,
    window: tuple[datetime, datetime],
    *,
    store: ResultsStore,
    panel: pd.DataFrame | None = None,
    method: Literal["auto", "granger", "pcmci_plus"] = "auto",
    use_llm: bool = True,
    segment_df: pd.DataFrame | None = None,
    dimension: str | None = None,
) -> MovementExplanation:
    """Produce a two-channel reconciliation explanation for a metric movement.

    Args:
        metric_fqn:  Fully-qualified metric name.
        window:      (start, end) datetime tuple for the analysis window.
        store:       ResultsStore to query failed checks and metric runs.
        panel:       Optional panel DataFrame for Channel B causal analysis.
                     Columns = metric names, index = datetime.
        method:      Causal method override.
        use_llm:     Whether to attempt LLM narrative (falls back to template).
        segment_df:  Optional segment DataFrame for mix-shift decomposition.
        dimension:   Label for the segment dimension (required if segment_df given).
    """
    window_start, window_end = window

    # Channel A -- data integrity
    data_issues = scan_channel_a(metric_fqn, window_start, window_end, store)

    # Channel B -- business drivers
    if panel is not None and not panel.empty:
        ch_b = analyze_channel_b(
            metric_fqn, panel,
            method=method,
            segment_df=segment_df,
            dimension=dimension,
        )
    else:
        ch_b = ChannelBReport(
            business_drivers=[], mix_shift=None, ruled_out=[], estimated_contribution=(0.0, 0.05)
        )

    # Observed change from stored MetricRun values
    observed_change = _estimate_observed_change(metric_fqn, window_start, window_end, store)

    # Contribution totals
    data_lo, data_hi = (
        (min(1.0, sum(i.contribution_low for i in data_issues)),
         min(1.0, sum(i.contribution_high for i in data_issues)))
        if data_issues else (0.0, 0.0)
    )
    biz_lo, biz_hi = ch_b.estimated_contribution

    # Determine primary channel
    if data_hi >= 0.30 and data_hi >= biz_hi:
        primary_channel: Literal["data", "business", "mixed"] = "data"
    elif biz_hi >= 0.20 and biz_hi > data_hi:
        primary_channel = "business"
    else:
        primary_channel = "mixed"

    explanation = MovementExplanation(
        metric_fqn=metric_fqn,
        window_start=window_start,
        window_end=window_end,
        observed_change=observed_change,
        data_issues=data_issues,
        estimated_data_contribution=(data_lo, data_hi),
        business_drivers=ch_b.business_drivers,
        mix_shift=ch_b.mix_shift,
        ruled_out=ch_b.ruled_out,
        estimated_business_contribution=(biz_lo, biz_hi),
        summary_paragraph="",
        primary_channel=primary_channel,
        citations={},
        computation_metadata={
            "method": method,
            "n_data_issues": len(data_issues),
            "n_business_drivers": len(ch_b.business_drivers),
        },
    )

    if use_llm:
        explanation = generate_narrative(explanation)
    else:
        explanation = _apply_template(explanation)

    return explanation


def _estimate_observed_change(
    metric_fqn: str,
    window_start: datetime,
    window_end: datetime,
    store: ResultsStore,
) -> float:
    """Estimate observed change from stored MetricRun values. Returns 0.0 if no data."""
    try:
        lookback = max(1, (window_end - window_start).days + 1)
        runs = store.list_metric_runs(metric_fqn, lookback_days=lookback + 7)
    except Exception:
        return 0.0
    if len(runs) < 2:
        return 0.0
    first_val = runs[0].value
    last_val = runs[-1].value
    if first_val == 0:
        return 0.0
    return (last_val - first_val) / abs(first_val)
