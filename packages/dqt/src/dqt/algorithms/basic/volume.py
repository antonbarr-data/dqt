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

    def get_aggregations(self, col: str, dialect: str = "ansi") -> list[AggExpr]:
        return [AggExpr(name="row_count", sql="COUNT(*)")]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {"baseline_count": int(reference.iloc[0]["row_count"])}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr_count = int(current.iloc[0]["row_count"])
        base_count = state.get("baseline_count")
        if base_count is None:
            from dqt.algorithms._base import Verdict
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english=f"Row count {curr_count:,} (no baseline yet — will compare on next run)",
                details={"current_count": curr_count},
            )
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


@registry.register
class VolumeAnomalyDetector(BaseAggregateDetector):
    """Checks that row count is within [min_rows, max_rows].
    Declarative — no baseline needed. Fails if count is 0 by default.
    """
    slug = "volume_anomaly"
    group = "basic"

    def __init__(self, min_rows: int = 1, max_rows: int = 2**31) -> None:
        self._min = int(min_rows)
        self._max = int(max_rows)

    def get_aggregations(self, col: str, dialect: str = "ansi") -> list[AggExpr]:
        return [AggExpr(name="row_count", sql="COUNT(*)")]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        count = int(current.iloc[0]["row_count"])
        in_range = self._min <= count <= self._max
        score = 0.0 if in_range else 1.0
        from dqt.algorithms._base import compute_verdict
        direction = "above" if count > self._max else "below"
        return DetectorResult(
            score=score,
            verdict=compute_verdict(score, "volume_anomaly"),
            plain_english=(
                f"Row count {count:,} {'within' if in_range else direction + ' the'} "
                f"expected range [{self._min:,}, {self._max:,}]"
            ),
            details={"row_count": count, "min_rows": self._min, "max_rows": self._max},
        )


@registry.register
class RowCountInRangeDetector(BaseAggregateDetector):
    """Checks that row count in a date window falls within [min_rows, max_rows].

    Declarative check — no baseline needed. Useful for SLA checks like
    "marketing_campaigns must have 50-500 rows per day."
    """
    slug = "row_count_in_range"
    group = "basic"

    def __init__(
        self,
        date_col: str,
        start_date: str,
        end_date: str,
        min_rows: int = 0,
        max_rows: int = 2**31,
    ) -> None:
        self._date_col = date_col
        self._start = start_date
        self._end = end_date
        self._min = min_rows
        self._max = max_rows

    def get_aggregations(self, col: str, dialect: str = "ansi") -> list[AggExpr]:
        # Portable SQL: no FILTER(WHERE...) to work on MySQL / BigQuery / Redshift
        return [
            AggExpr(
                name="windowed_count",
                sql=(
                    f"SUM(CASE WHEN {self._date_col} >= '{self._start}'"
                    f" AND {self._date_col} <= '{self._end}'"
                    f" THEN 1 ELSE 0 END)"
                ),
            )
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        count = int(current.iloc[0]["windowed_count"] or 0)
        in_range = self._min <= count <= self._max
        score = 0.0 if in_range else 1.0
        from dqt.algorithms._base import compute_verdict
        verdict = compute_verdict(score, "row_count_in_range")
        direction = "above" if count > self._max else "below"
        plain = (
            f"{count:,} rows in {self._date_col}[{self._start}, {self._end}] "
            f"{'within' if in_range else direction + ' the'} expected range [{self._min:,}, {self._max:,}]"
        )
        return DetectorResult(
            score=score,
            verdict=verdict,
            plain_english=plain,
            details={
                "actual_count": count,
                "min_rows": self._min,
                "max_rows": self._max,
                "date_col": self._date_col,
                "start_date": self._start,
                "end_date": self._end,
            },
            failing_filter_sql=(
                None if in_range else
                f"{self._date_col} >= '{self._start}' AND {self._date_col} <= '{self._end}'"
            ),
        )
