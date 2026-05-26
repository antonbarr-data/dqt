# Ref: Kolmogorov (1933), Smirnov (1948) — two-sample KS test via scipy.stats.ks_2samp
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from datetime import date, timedelta
from typing import ClassVar

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry


@registry.register
class KS2SampleDetector(BaseDetector):
    """Two-sample KS test for distribution drift. Score = 1 − p-value; warn p<0.05, fail p<0.01."""
    slug = "ks_pvalue"
    group = "drift"
    min_recommended_n: ClassVar[int] = 500

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {"reference": reference.iloc[:, 0].dropna().to_numpy(dtype=float)}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        if len(curr) == 0 or len(state["reference"]) == 0:
            return DetectorResult(
                score=0.0,
                verdict=Verdict.pass_,
                plain_english="Insufficient data for KS test.",
                details={"p_value": 1.0, "ks_statistic": 0.0},
            )
        ks_stat, p_value = stats.ks_2samp(state["reference"], curr)
        score = 1.0 - float(p_value)
        return DetectorResult(
            score=score,
            verdict=self._verdict(score),
            plain_english=(
                f"KS p={p_value:.4f} (n_ref={len(state['reference'])}, n_curr={len(curr)}) — "
                f"{'drift detected' if score > 0.95 else 'no significant drift'}"
            ),
            details={"ks_statistic": float(ks_stat), "p_value": float(p_value)},
        )


@registry.register
class KSDriftDetector(BaseDetector):
    """Time-windowed KS drift check: compares a reference window vs. a current window.

    reference window: [today - current_days - reference_days, today - current_days - 1]
    current window:   [today - current_days, today]
    """
    slug = "ks_drift"
    group = "drift"
    min_recommended_n: ClassVar[int] = 100

    def __init__(
        self,
        date_col: str,
        reference_days: int = 30,
        current_days: int = 7,
    ) -> None:
        import re
        if not date_col or not str(date_col).strip():
            raise ValueError("KSDriftDetector requires a non-empty date_col (the date/timestamp column to filter by).")
        stripped = str(date_col).strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}$", stripped):
            raise ValueError(
                f"date_col must be a column NAME (e.g. 'created_at'), "
                f"not a date value ('{stripped}'). "
                f"Set it to the name of the date/timestamp column in your table."
            )
        self._date_col = stripped
        self._reference_days = int(reference_days)
        self._current_days = int(current_days)

    def get_sample_filters(self) -> tuple[str, str]:
        """Return (reference_where, current_where) SQL WHERE fragments for the two windows."""
        today = date.today()
        curr_start = today - timedelta(days=self._current_days - 1)
        ref_end = curr_start - timedelta(days=1)
        ref_start = ref_end - timedelta(days=self._reference_days - 1)
        ref_where = f"{self._date_col} >= '{ref_start}' AND {self._date_col} <= '{ref_end}'"
        curr_where = f"{self._date_col} >= '{curr_start}' AND {self._date_col} <= '{today}'"
        return ref_where, curr_where

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {"reference": reference.iloc[:, 0].dropna().to_numpy(dtype=float)}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        ref = state["reference"]
        if len(curr) == 0 or len(ref) == 0:
            return DetectorResult(
                score=0.0,
                verdict=Verdict.pass_,
                plain_english="Insufficient data for KS drift test.",
                details={"p_value": 1.0, "ks_statistic": 0.0},
            )
        ks_stat, p_value = stats.ks_2samp(ref, curr)
        score = 1.0 - float(p_value)
        today = date.today()
        curr_start = today - timedelta(days=self._current_days - 1)
        ref_end = curr_start - timedelta(days=1)
        ref_start = ref_end - timedelta(days=self._reference_days - 1)
        return DetectorResult(
            score=score,
            verdict=self._verdict(score),
            plain_english=(
                f"KS p={p_value:.4f}: {self._date_col} [{curr_start}, {today}] vs "
                f"[{ref_start}, {ref_end}] (n_ref={len(ref)}, n_curr={len(curr)}) — "
                f"{'drift detected' if score > 0.95 else 'no significant drift'}"
            ),
            details={
                "ks_statistic": float(ks_stat),
                "p_value": float(p_value),
                "reference_window": f"{ref_start}/{ref_end}",
                "current_window": f"{curr_start}/{today}",
            },
        )
