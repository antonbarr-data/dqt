# packages/dqt/src/dqt/algorithms/drift/adwin.py
# Ref: Bifet & Gavalda (2007) SDM — Learning from Time-Changing Data with Adaptive Windowing
# Combines reference + current into a stream; checks all cut-points for mean difference
# using Hoeffding's bound. Score = 1.0 if drift detected, 0.0 otherwise.
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry


def _hoeffding_bound(n0: int, n1: int, delta: float) -> float:
    m = 1.0 / (1.0 / n0 + 1.0 / n1)
    return float(np.sqrt(np.log(2.0 / delta) / (2.0 * m)))


@registry.register
class ADWINDetector(BaseDetector):
    """Adaptive Windowing (ADWIN) drift detector. Score = 1.0 if drift detected, 0.0 if stable."""
    slug = "adwin"
    group = "drift"

    def __init__(self, delta: float = 0.002) -> None:
        self._delta = delta

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        ref = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        return {
            "reference": ref,
            "ref_mean": float(np.mean(ref)),
            "delta": self._delta,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        ref = state["reference"]
        if len(curr) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={
                    "drift_detected": False,
                    "ref_mean": state["ref_mean"],
                    "curr_mean": float("nan"),
                    "n_windows_checked": 0,
                },
            )
        delta = state["delta"]
        drift_detected = False
        n_checked = 0
        detected_mean0 = float("nan")
        detected_mean1 = float("nan")
        # Check the ref|curr boundary using Hoeffding's bound.
        # Also check geometric sub-cuts within ref and within curr to catch
        # partial distribution changes, but only on the same side of the boundary.
        n0_base = len(ref)
        n1_base = len(curr)
        combined = np.concatenate([ref, curr])
        n = len(combined)
        cumsum = np.cumsum(combined)
        # Build candidate cut-points: the natural boundary + geometric subdivisions
        # of each half, requiring a minimum window size to avoid noise on tiny tails.
        min_window = max(30, int(0.05 * n))
        candidate_cuts = sorted(set(
            [n0_base]
            + [max(min_window, int(n0_base * (1 - 2**(-k)))) for k in range(1, 10)]
            + [min(n - min_window, n0_base + int(n1_base * 2**(-k))) for k in range(1, 10)]
        ))
        for cut in candidate_cuts:
            n0 = cut
            n1 = n - cut
            if n0 < min_window or n1 < min_window:
                continue
            eps = _hoeffding_bound(n0, n1, delta)
            mean0 = cumsum[n0 - 1] / n0
            mean1 = (cumsum[-1] - cumsum[n0 - 1]) / n1
            mean_diff = abs(mean0 - mean1)
            n_checked += 1
            if mean_diff > eps:
                drift_detected = True
                detected_mean0 = mean0
                detected_mean1 = mean1
                break
        score = 1.0 if drift_detected else 0.0
        curr_mean = float(np.mean(curr))
        if drift_detected:
            means_str = f"window_before={detected_mean0:.4f}, window_after={detected_mean1:.4f}"
        else:
            means_str = f"ref_mean={state['ref_mean']:.4f}, curr_mean={curr_mean:.4f}"
        return DetectorResult(
            score=score,
            verdict=self._verdict(score),
            plain_english=f"ADWIN: {'drift detected' if drift_detected else 'stable'} ({means_str})",
            details={
                "drift_detected": drift_detected,
                "ref_mean": state["ref_mean"],
                "curr_mean": curr_mean,
                "n_windows_checked": n_checked,
            },
        )
