from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


def _binary_result(value: float, min_val: float, max_val: float, label: str, slug: str) -> DetectorResult:
    in_range = min_val <= value <= max_val
    score = 0.0 if in_range else 1.0
    from dqt.algorithms._base import compute_verdict
    return DetectorResult(
        score=score,
        verdict=compute_verdict(score, slug),
        plain_english=(
            f"{label} {value:.4g} is {'within' if in_range else 'outside'} bounds [{min_val:.4g}, {max_val:.4g}]"
        ),
        details={"value": value, "min_bound": min_val, "max_bound": max_val},
    )


@registry.register
class MaxInRangeDetector(BaseAggregateDetector):
    """Verifies MAX(col) is within [min_val, max_val]."""
    slug = "max_in_range"
    group = "basic"

    def __init__(self, min_val: float = 0.0, max_val: float = float("inf")) -> None:
        self._min, self._max = min_val, max_val

    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [AggExpr(name="agg_value", sql=f"MAX({col})")]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return _binary_result(float(current.iloc[0]["agg_value"]), self._min, self._max, "MAX", "max_in_range")


@registry.register
class MinInRangeDetector(BaseAggregateDetector):
    """Verifies MIN(col) is within [min_val, max_val]."""
    slug = "min_in_range"
    group = "basic"

    def __init__(self, min_val: float = 0.0, max_val: float = float("inf")) -> None:
        self._min, self._max = min_val, max_val

    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [AggExpr(name="agg_value", sql=f"MIN({col})")]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return _binary_result(float(current.iloc[0]["agg_value"]), self._min, self._max, "MIN", "min_in_range")


@registry.register
class MedianInRangeDetector(BaseAggregateDetector):
    """Verifies PERCENTILE_CONT(0.5) of col is within [min_val, max_val]."""
    slug = "median_in_range"
    group = "basic"

    def __init__(self, min_val: float = 0.0, max_val: float = float("inf")) -> None:
        self._min, self._max = min_val, max_val

    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [AggExpr(name="agg_value", sql=f"PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {col})")]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return _binary_result(float(current.iloc[0]["agg_value"]), self._min, self._max, "Median", "median_in_range")


@registry.register
class StdDevInRangeDetector(BaseAggregateDetector):
    """Verifies STDDEV(col) is within [min_val, max_val]."""
    slug = "stddev_in_range"
    group = "basic"

    def __init__(self, min_val: float = 0.0, max_val: float = float("inf")) -> None:
        self._min, self._max = min_val, max_val

    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [AggExpr(name="agg_value", sql=f"STDDEV({col})")]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return _binary_result(float(current.iloc[0]["agg_value"] or 0), self._min, self._max, "Stddev", "stddev_in_range")


@registry.register
class SumInRangeDetector(BaseAggregateDetector):
    """Verifies SUM(col) is within [min_val, max_val]."""
    slug = "sum_in_range"
    group = "basic"

    def __init__(self, min_val: float = 0.0, max_val: float = float("inf")) -> None:
        self._min, self._max = min_val, max_val

    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [AggExpr(name="agg_value", sql=f"SUM({col})")]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return _binary_result(float(current.iloc[0]["agg_value"] or 0), self._min, self._max, "SUM", "sum_in_range")


@registry.register
class CardinalityInRangeDetector(BaseAggregateDetector):
    """Verifies COUNT(DISTINCT col) is within [min_val, max_val]."""
    slug = "cardinality_in_range"
    group = "basic"

    def __init__(self, min_val: int = 1, max_val: int = 2**31) -> None:
        self._min, self._max = float(min_val), float(max_val)

    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [AggExpr(name="agg_value", sql=f"COUNT(DISTINCT {col})")]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return _binary_result(float(current.iloc[0]["agg_value"]), self._min, self._max, "Cardinality", "cardinality_in_range")


@registry.register
class QuantileInRangeDetector(BaseAggregateDetector):
    """Verifies a specified quantile of col is within [min_val, max_val]."""
    slug = "quantile_in_range"
    group = "basic"

    def __init__(self, quantile: float = 0.95, min_val: float = 0.0, max_val: float = float("inf")) -> None:
        self._q, self._min, self._max = quantile, min_val, max_val

    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [AggExpr(name="agg_value", sql=f"PERCENTILE_CONT({self._q}) WITHIN GROUP (ORDER BY {col})")]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        label = f"p{int(self._q * 100)}"
        return _binary_result(float(current.iloc[0]["agg_value"]), self._min, self._max, label, "quantile_in_range")
