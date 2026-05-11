# packages/dqt/src/dqt/algorithms/timeseries/matrix_profile.py
# Ref: Yeh et al. (2016) ICDM — Matrix Profile I: Motifs, Discords, and Shapelets
# Ref: Law (2019) JOSS — STUMPY: A Powerful and Scalable Python Library for Time Series Data Mining
# stumpy if installed; falls back to brute-force z-normalised Euclidean 1-NN distance.
# Score = fraction of current subsequences with 1-NN dist above reference 95th percentile.
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_EPSILON = 1e-8


def _znorm(x: np.ndarray) -> np.ndarray:
    mu = x.mean()
    sigma = x.std()
    return (x - mu) / max(sigma, _EPSILON)


def _extract_subsequences(values: np.ndarray, window: int) -> np.ndarray:
    n = len(values)
    if n < window:
        return np.empty((0, window))
    return np.array([values[i: i + window] for i in range(n - window + 1)])


def _nn_distances_numpy(
    query_subsequences: np.ndarray,
    reference_subsequences: np.ndarray,
    exclusion_zone: int = 0,
) -> np.ndarray:
    """Brute-force 1-NN z-normalised Euclidean distance.

    exclusion_zone: when query and reference are the same array, exclude
    indices within exclusion_zone of each query index to avoid trivial self-matches.
    """
    ref_znorm = np.array([_znorm(s) for s in reference_subsequences])
    n_query = len(query_subsequences)
    n_ref = len(ref_znorm)
    distances = np.empty(n_query)
    for i, qs in enumerate(query_subsequences):
        qz = _znorm(qs)
        diffs = ref_znorm - qz
        dists = np.sqrt(np.sum(diffs ** 2, axis=1))
        if exclusion_zone > 0:
            lo = max(0, i - exclusion_zone)
            hi = min(n_ref, i + exclusion_zone + 1)
            dists[lo:hi] = np.inf
        finite = dists[np.isfinite(dists)]
        distances[i] = float(np.min(finite)) if len(finite) > 0 else 0.0
    return distances


@registry.register
class MatrixProfileDetector(BaseDetector):
    """Matrix Profile discord detector. Score = fraction of current subsequences with 1-NN dist above reference 95th pct."""
    slug = "matrix_profile"
    group = "timeseries"

    def __init__(self, window: int = 7) -> None:
        self._window = window

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        values = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        if len(values) < self._window:
            raise ValueError(
                f"MatrixProfile requires at least {self._window} reference observations, got {len(values)}"
            )
        try:
            import stumpy  # type: ignore[import]
            mp = stumpy.stump(values, m=self._window)
            ref_distances = mp[:, 0].astype(float)
            backend = "stumpy"
        except ImportError:
            # Exclusion zone = window // 2 to avoid trivial self-matches (standard MP convention).
            excl = self._window // 2
            subsequences = _extract_subsequences(values, self._window)
            ref_distances = _nn_distances_numpy(subsequences, subsequences, exclusion_zone=excl)
            backend = "numpy"

        # 99th percentile: cross-match distances (current vs reference) are inherently
        # higher than self-distances (exclusion-zone-corrected) on the same series.
        # Using p99 aligns the threshold with the tail of the cross-match distribution.
        threshold = float(np.percentile(ref_distances, 99))
        return {
            "reference": values,
            "threshold": threshold,
            "window": self._window,
            "backend": backend,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        values = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        window = state["window"]
        if len(values) < window:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english=f"Not enough data for window={window}.",
                details={
                    "discord_fraction": 0.0,
                    "distance_threshold": state["threshold"],
                    "window": window,
                    "backend": state["backend"],
                },
            )
        ref_subs = _extract_subsequences(state["reference"], window)
        curr_subs = _extract_subsequences(values, window)
        if len(curr_subs) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english=f"No subsequences extracted with window={window}.",
                details={
                    "discord_fraction": 0.0,
                    "distance_threshold": state["threshold"],
                    "window": window,
                    "backend": state["backend"],
                },
            )
        curr_distances = _nn_distances_numpy(curr_subs, ref_subs)
        n_discord = int(np.sum(curr_distances > state["threshold"]))
        frac = n_discord / len(curr_distances)
        return DetectorResult(
            score=frac,
            verdict=self._verdict(frac),
            plain_english=(
                f"{n_discord} of {len(curr_distances)} subsequences are discords "
                f"(distance > {state['threshold']:.3f}; {frac:.1%}); "
                f"backend={state['backend']}"
            ),
            details={
                "discord_fraction": frac,
                "distance_threshold": state["threshold"],
                "window": window,
                "backend": state["backend"],
            },
        )
