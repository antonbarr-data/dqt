# Base classes for all detectors. StatScale and STAT_SCALES live in _scales.py (no dqt imports there).
# compute_verdict defers the _scales import to break any potential circular dependency.
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

import pandas as pd

if TYPE_CHECKING:
    from dqt.adapters._protocol import AggExpr


class Verdict(str, Enum):
    pass_ = "pass"
    warn = "warn"
    fail = "fail"


@dataclass
class DetectorResult:
    score: float
    verdict: Verdict
    plain_english: str
    details: dict[str, Any] = field(default_factory=dict)
    # WHERE clause (no "WHERE" keyword) identifying failing rows; runner constructs full SQL
    failing_filter_sql: str | None = None


DetectorState = Any


@dataclass
class CostEstimate:
    """Resource estimate for one detector run against one table."""
    rows_scanned: int
    warehouse_cost_usd: float  # 0.0 for local/DuckDB execution; non-zero for cloud warehouses
    wall_time_seconds: float   # rough wall-clock estimate


def compute_verdict(
    score: float,
    slug: str,
    warn_threshold: float | None = None,
    fail_threshold: float | None = None,
) -> Verdict:
    from dqt.algorithms._scales import STAT_SCALES  # deferred to avoid circular deps
    scale = STAT_SCALES.get(slug)
    if scale is None:
        raise KeyError(f"No STAT_SCALE entry for slug '{slug}'. Add it to _scales.py.")
    warn = warn_threshold if warn_threshold is not None else scale.warn_threshold
    fail = fail_threshold if fail_threshold is not None else scale.fail_threshold
    if scale.direction == "lower_is_better":
        if score >= fail:
            return Verdict.fail
        if score >= warn:
            return Verdict.warn
        return Verdict.pass_
    else:
        if score <= fail:
            return Verdict.fail
        if score <= warn:
            return Verdict.warn
        return Verdict.pass_


class BaseDetector:
    slug: ClassVar[str]
    group: ClassVar[str]
    kind: ClassVar[str] = "sample"
    # Bump version when the scoring algorithm changes so the runner can detect
    # stale baselines and automatically re-fit them.
    version: ClassVar[str] = "1"
    # Minimum N for reliable results. Runner prepends a low-power warning when
    # len(current_df) < min_recommended_n.
    min_recommended_n: ClassVar[int] = 30

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        raise NotImplementedError

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        raise NotImplementedError

    def _verdict(self, score: float) -> Verdict:
        return compute_verdict(score, self.slug)

    def suggest_threshold(
        self,
        reference_df: "pd.DataFrame",
        target_fpr: float = 0.001,
        n_bootstrap: int = 200,
    ) -> dict:
        """Bootstrap-calibrate a score threshold for target false-positive rate on clean data."""
        from dqt.algorithms._calibration import suggest_threshold as _suggest
        return _suggest(self, reference_df, target_fpr=target_fpr, n_bootstrap=n_bootstrap)

    def estimate_cost(self, row_count: int, sample_n: int = 100_000) -> CostEstimate:
        """Return a resource estimate for running this detector on a table.

        Default implementation assumes local DuckDB execution (no warehouse cost).
        Detectors that push work to the warehouse should override this method.

        Args:
            row_count: total rows in the target table (from adapter.describe_columns or info_schema)
            sample_n: configured sample size for this check
        """
        rows = min(row_count, sample_n)
        return CostEstimate(
            rows_scanned=rows,
            warehouse_cost_usd=0.0,
            wall_time_seconds=rows * 2e-5,  # ~50k rows/sec for typical stat computation
        )


class BaseAggregateDetector(BaseDetector):
    kind: ClassVar[str] = "aggregate"

    def get_aggregations(self, col: str) -> list[AggExpr]:
        raise NotImplementedError

    def estimate_cost(self, row_count: int, sample_n: int = 100_000) -> CostEstimate:
        # Aggregate detectors push a single SQL aggregate — near-zero cost.
        return CostEstimate(rows_scanned=row_count, warehouse_cost_usd=0.0, wall_time_seconds=0.1)
