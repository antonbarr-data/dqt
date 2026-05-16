"""Mix-shift decomposition.

Given a DataFrame with columns [window (before/after), segment, share, value],
splits an aggregate metric's movement into:
  - Mix effect:   change in segment shares at constant per-segment values
  - Level effect: change in per-segment values at constant shares

Reference: Oaxaca-Blinder decomposition (bivariate version).
"""
from __future__ import annotations

import pandas as pd

from dqt.insights.models import EvidenceRow, MixShiftReport


def decompose(df: pd.DataFrame, dimension: str) -> MixShiftReport | None:
    """Decompose aggregate movement over `dimension` into mix vs level effects.

    Args:
        df: rows with columns: window ('before'/'after'), segment (str), share (float), value (float)
        dimension: human-readable label for the dimension (e.g. "region")

    Returns:
        MixShiftReport or None if data is insufficient.
    """
    if df.empty or not {"window", "segment", "share", "value"}.issubset(df.columns):
        return None

    before = df[df["window"] == "before"].set_index("segment")
    after = df[df["window"] == "after"].set_index("segment")
    if before.empty or after.empty:
        return None

    segments = sorted(set(before.index) | set(after.index))
    segment_rows: list[dict] = []
    for seg in segments:
        sb = float(before.loc[seg, "share"]) if seg in before.index else 0.0
        sa = float(after.loc[seg, "share"]) if seg in after.index else 0.0
        vb = float(before.loc[seg, "value"]) if seg in before.index else 0.0
        va = float(after.loc[seg, "value"]) if seg in after.index else vb
        segment_rows.append({"segment": seg, "share_before": sb, "share_after": sa,
                              "value_before": vb, "value_after": va})

    # Counterfactual: what would aggregate be with after-shares but before-values?
    agg_before = sum(r["share_before"] * r["value_before"] for r in segment_rows)
    agg_counterfactual = sum(r["share_after"] * r["value_before"] for r in segment_rows)
    agg_after = sum(r["share_after"] * r["value_after"] for r in segment_rows)

    if agg_before == 0:
        return None

    total_change = (agg_after - agg_before) / abs(agg_before)
    mix_fraction = abs((agg_counterfactual - agg_before) / agg_before) / (abs(total_change) + 1e-9)
    mix_fraction = min(mix_fraction, 1.0)

    low = max(0.0, mix_fraction - 0.15)
    high = min(1.0, mix_fraction + 0.15)

    evidence = EvidenceRow(
        source=f"mix_shift:{dimension}",
        signal_type="mix_shift",
        magnitude=mix_fraction,
        magnitude_low=low,
        magnitude_high=high,
        evidence_strength="strong" if mix_fraction > 0.5 else "moderate",
        detail={"dimension": dimension, "agg_before": agg_before, "agg_after": agg_after,
                "agg_counterfactual": agg_counterfactual},
    )
    return MixShiftReport(
        dimension=dimension,
        segments=segment_rows,
        mix_contribution_low=low,
        mix_contribution_high=high,
        evidence=evidence,
    )
