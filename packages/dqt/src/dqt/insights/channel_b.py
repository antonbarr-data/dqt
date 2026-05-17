"""Channel B: business driver analysis.

Auto-routes by number of candidate columns:
  1-3  -> Granger pairwise (fast)
  4+   -> PCMCI+ (controls confounders; requires tigramite); falls back to Granger if not installed

Returns RankedCause list sorted by causal evidence strength.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from dqt.insights.models import EvidenceRow, RankedCause, RuledOutItem, MixShiftReport


@dataclass
class ChannelBReport:
    business_drivers: list[RankedCause]
    mix_shift: MixShiftReport | None
    ruled_out: list[RuledOutItem]
    estimated_contribution: tuple[float, float]


_STRENGTH_CONTRIBUTION = {
    "strong":   (0.20, 0.50),
    "moderate": (0.10, 0.30),
    "weak":     (0.02, 0.10),
    "none":     (0.00, 0.02),
}


def analyze(
    target_col: str,
    panel: pd.DataFrame,
    *,
    method: Literal["auto", "granger", "pcmci_plus"] = "auto",
    segment_df: pd.DataFrame | None = None,
    dimension: str | None = None,
) -> ChannelBReport:
    """Analyze business drivers for `target_col` in `panel`."""
    if panel.empty or target_col not in panel.columns:
        return ChannelBReport(
            business_drivers=[], mix_shift=None, ruled_out=[],
            estimated_contribution=(0.0, 0.0),
        )

    candidates = [c for c in panel.columns if c != target_col]
    n_candidates = len(candidates)

    if method == "auto":
        method = "granger" if n_candidates <= 3 else "pcmci_plus"

    drivers: list[RankedCause] = []
    ruled_out: list[RuledOutItem] = []

    if method == "granger":
        drivers, ruled_out = _run_granger(target_col, panel, candidates)
    elif method == "pcmci_plus":
        try:
            import tigramite  # noqa: F401 — availability check
            drivers, ruled_out = _run_pcmci(target_col, panel, candidates)
        except ImportError:
            drivers, ruled_out = _run_granger(target_col, panel, candidates)

    drivers.sort(key=lambda d: d.contribution_high, reverse=True)

    mix_shift = None
    if segment_df is not None and dimension is not None:
        from dqt.insights.mixshift import decompose
        mix_shift = decompose(segment_df, dimension)

    if drivers:
        agg_low = min(1.0, sum(d.contribution_low for d in drivers))
        agg_high = min(1.0, sum(d.contribution_high for d in drivers))
    else:
        agg_low, agg_high = 0.0, 0.05

    return ChannelBReport(
        business_drivers=drivers,
        mix_shift=mix_shift,
        ruled_out=ruled_out,
        estimated_contribution=(agg_low, agg_high),
    )


def _run_granger(
    target_col: str,
    panel: pd.DataFrame,
    candidates: list[str],
) -> tuple[list[RankedCause], list[RuledOutItem]]:
    drivers: list[RankedCause] = []
    ruled_out: list[RuledOutItem] = []
    try:
        from dqt.causality import granger_pairwise
        report = granger_pairwise(panel, max_lag=4, significance_level=0.05)
    except Exception as exc:
        return [], [RuledOutItem(c, f"granger failed: {exc}") for c in candidates]

    for edge in report.edges:
        if edge.effect != target_col:
            continue
        low, high = _STRENGTH_CONTRIBUTION.get(edge.evidence_strength, (0.0, 0.02))
        if edge.significant:
            evidence = EvidenceRow(
                source=f"granger:{edge.cause}->{edge.effect}",
                signal_type="causal_edge",
                magnitude=(low + high) / 2,
                magnitude_low=low,
                magnitude_high=high,
                evidence_strength=edge.evidence_strength,
                detail={
                    "p_value": edge.adjusted_p_value,
                    "f_statistic": edge.f_statistic,
                    "selected_lag": edge.selected_lag,
                },
            )
            drivers.append(RankedCause(
                cause_metric_fqn=edge.cause,
                lag_periods=edge.selected_lag,
                p_value=edge.adjusted_p_value,
                evidence_strength=edge.evidence_strength,
                contribution_low=low,
                contribution_high=high,
                evidence=evidence,
            ))
        else:
            ruled_out.append(RuledOutItem(
                edge.cause,
                f"p_value={edge.adjusted_p_value:.3f} (not significant at alpha=0.05)",
            ))
    return drivers, ruled_out


def _run_pcmci(
    target_col: str,
    panel: pd.DataFrame,
    candidates: list[str],
) -> tuple[list[RankedCause], list[RuledOutItem]]:
    drivers: list[RankedCause] = []
    ruled_out: list[RuledOutItem] = []
    try:
        from dqt.causality import pcmci_pairwise
        report = pcmci_pairwise(panel, significance_level=0.05)
    except Exception:
        return _run_granger(target_col, panel, candidates)

    for edge in report.edges:
        if edge.effect != target_col:
            continue
        low, high = _STRENGTH_CONTRIBUTION.get(edge.evidence_strength, (0.0, 0.02))
        if edge.significant:
            evidence = EvidenceRow(
                source=f"pcmci:{edge.cause}->{edge.effect}",
                signal_type="causal_edge",
                magnitude=(low + high) / 2,
                magnitude_low=low,
                magnitude_high=high,
                evidence_strength=edge.evidence_strength,
                detail={
                    "p_value": edge.adjusted_p_value,
                    "lag": edge.lag,
                },
            )
            drivers.append(RankedCause(
                cause_metric_fqn=edge.cause,
                lag_periods=edge.lag,
                p_value=edge.adjusted_p_value,
                evidence_strength=edge.evidence_strength,
                contribution_low=low,
                contribution_high=high,
                evidence=evidence,
            ))
        else:
            ruled_out.append(RuledOutItem(
                edge.cause,
                f"p_value={edge.adjusted_p_value:.3f} (not significant at alpha=0.05)",
            ))
    return drivers, ruled_out
