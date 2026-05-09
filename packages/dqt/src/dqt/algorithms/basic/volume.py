from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class VolumeDetector(BaseAggregateDetector):
    """Detects anomalous row count changes relative to the baseline window."""
    slug = "volume"
    group = "basic"

    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [AggExpr(name="row_count", sql="COUNT(*)")]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {"baseline_count": int(reference.iloc[0]["row_count"])}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr_count = int(current.iloc[0]["row_count"])
        base_count = state["baseline_count"]
        ratio = abs(curr_count / base_count - 1.0) if base_count > 0 else 0.0
        return DetectorResult(
            score=ratio,
            verdict=self._verdict(ratio),
            plain_english=f"Row count {curr_count:,} is {ratio:.1%} {'above' if curr_count > base_count else 'below'} baseline ({base_count:,})",
            details={"current_count": curr_count, "baseline_count": base_count, "change_ratio": ratio},
        )

    def _verdict(self, score: float):
        from dqt.algorithms._base import compute_verdict
        return compute_verdict(score, "volume_change_ratio")
