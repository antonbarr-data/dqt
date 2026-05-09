from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class MonotonicityDetector(BaseDetector):
    """
    Checks that values in the first numeric column of the DataFrame are
    non-decreasing (increasing) or non-increasing (decreasing).
    Score: 0.0 = monotonic, 1.0 = not monotonic.
    """
    slug = "monotonicity"
    group = "basic"

    def __init__(self, direction: Literal["increasing", "decreasing"] = "increasing") -> None:
        self._direction = direction

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {"direction": self._direction}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        values = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        direction = state["direction"]
        if direction == "increasing":
            is_monotonic = bool(np.all(np.diff(values) >= 0))
        else:
            is_monotonic = bool(np.all(np.diff(values) <= 0))
        score = 0.0 if is_monotonic else 1.0
        from dqt.algorithms._base import compute_verdict
        return DetectorResult(
            score=score,
            verdict=compute_verdict(score, "monotonicity_violation"),
            plain_english=f"Sequence is {'monotonically ' + direction if is_monotonic else 'NOT monotonically ' + direction}",
            details={"direction": direction, "is_monotonic": is_monotonic, "n_values": len(values)},
        )
