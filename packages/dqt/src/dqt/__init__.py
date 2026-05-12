# packages/dqt/src/dqt/__init__.py
"""dqt — open-source data quality, observability, and causality library."""
from __future__ import annotations

__version__ = "0.5.5"

from dqt.algorithms._base import (
    BaseAggregateDetector,
    BaseDetector,
    CostEstimate,
    DetectorResult,
    Verdict,
    compute_verdict,
)
from dqt.algorithms._calibration import ThresholdDriftResult, calibrate_from_history
from dqt.adapters._protocol import AggExpr, ColumnMeta, HealthCheckResult, WarehouseAdapter
from dqt.store._protocol import CausalEdgeReview, Incident, ResultsStore, RunResult
from dqt.store.memory import MemoryStore
from dqt.checks.models import BaselineConfig, Check, CheckFilter, CheckScope
from dqt.runner.runner import Runner, SuiteResult

# Import all detector groups to trigger @registry.register side effects
import dqt.algorithms.basic           # noqa: F401
import dqt.algorithms.schema          # noqa: F401
import dqt.algorithms.referential     # noqa: F401
import dqt.algorithms.drift           # noqa: F401
import dqt.algorithms.outliers_uni    # noqa: F401
import dqt.algorithms.outliers_multi  # noqa: F401
import dqt.algorithms.timeseries      # noqa: F401
import dqt.algorithms.info            # noqa: F401
import dqt.algorithms.pattern         # noqa: F401
import dqt.algorithms.custom          # noqa: F401

__all__ = [
    "__version__",
    "Verdict",
    "DetectorResult",
    "CostEstimate",
    "BaseDetector",
    "BaseAggregateDetector",
    "compute_verdict",
    "ThresholdDriftResult",
    "calibrate_from_history",
    "AggExpr",
    "ColumnMeta",
    "HealthCheckResult",
    "WarehouseAdapter",
    "ResultsStore",
    "RunResult",
    "Incident",
    "CausalEdgeReview",
    "MemoryStore",
    "Check",
    "CheckScope",
    "CheckFilter",
    "BaselineConfig",
    "Runner",
    "SuiteResult",
]
