from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry

_GRANULARITIES = {"day": "DAY", "week": "WEEK", "month": "MONTH", "hour": "HOUR"}


@registry.register
class DatePartCompletenessDetector(BaseAggregateDetector):
    """Checks that all expected date buckets within a lookback window contain at least one row.
    Dataplex parity: TimeSeriesAnomalyCheck (completeness variant).
    Score: fraction of expected buckets that have no data.
    """
    slug = "date_part_missing_fraction"
    group = "basic"

    def __init__(self, granularity: str = "day", lookback_days: int = 30) -> None:
        if granularity not in _GRANULARITIES:
            raise ValueError(f"granularity must be one of {set(_GRANULARITIES)}, got '{granularity}'")
        self._granularity = granularity
        self._lookback_days = lookback_days

    def get_aggregations(self, col: str, dialect: str = "ansi") -> list[AggExpr]:
        # CAST(col AS DATE) is portable across PostgreSQL, BigQuery, Snowflake.
        # GREATEST avoids negative values when more dates exist than the lookback period.
        # CASE WHEN instead of FILTER(WHERE...) for cross-database compatibility.
        return [
            AggExpr("missing_buckets", (
                f"GREATEST(0, {self._lookback_days} - "
                f"COUNT(DISTINCT CAST({col} AS DATE)))"
            )),
            AggExpr("total_buckets", str(self._lookback_days)),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        row = current.iloc[0]
        total = int(row["total_buckets"])
        missing = max(0, int(row["missing_buckets"]))
        frac = missing / total if total > 0 else 0.0
        return DetectorResult(
            score=frac,
            verdict=self._verdict(frac),
            plain_english=f"{missing}/{total} date buckets ({self._granularity}) have no data",
            details={"missing_buckets": missing, "total_buckets": total, "granularity": self._granularity},
        )
