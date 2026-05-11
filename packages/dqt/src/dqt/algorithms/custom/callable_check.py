# packages/dqt/src/dqt/algorithms/custom/callable_check.py
# Extension point: wrap any Python callable as a dqt detector.
# fn(df) -> float. Score is clipped to [0, 1].
from __future__ import annotations

from typing import Callable

import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry


@registry.register
class CallableCheckDetector(BaseDetector):
    """Wraps any Python callable (df -> float) as a dqt detector.

    Example::

        from dqt.algorithms.custom.callable_check import CallableCheckDetector

        def my_check(df):
            # return fraction of rows where col > 1000
            return (df["amount"] > 1000).mean()

        detector = CallableCheckDetector(fn=my_check)
        state = detector.fit(reference_df)
        result = detector.score(current_df, state)
    """

    slug = "callable_check"
    group = "custom"

    def __init__(self, fn: Callable[[pd.DataFrame], float]) -> None:
        if not callable(fn):
            raise TypeError(f"fn must be callable, got {type(fn)}")
        self._fn = fn

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        ref_score = float(self._fn(reference))
        return {"fn": self._fn, "ref_score": ref_score}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        score = float(state["fn"](current))
        score = min(max(score, 0.0), 1.0)
        return DetectorResult(
            score=score,
            verdict=self._verdict(score),
            plain_english=f"Callable check returned score={score:.4f} (ref={state['ref_score']:.4f})",
            details={"score": score, "ref_score": state["ref_score"]},
        )
