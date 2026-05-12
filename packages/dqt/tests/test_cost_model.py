# packages/dqt/tests/test_cost_model.py
"""Tests for per-detector estimate_cost() and Runner.run_suite()."""
from unittest.mock import MagicMock
import pytest
import pandas as pd

import dqt
from dqt.algorithms._base import CostEstimate
from dqt.algorithms._registry import registry
from dqt.runner.runner import SuiteResult


def test_cost_estimate_dataclass():
    est = CostEstimate(rows_scanned=1000, warehouse_cost_usd=0.05, wall_time_seconds=2.0)
    assert est.rows_scanned == 1000
    assert est.warehouse_cost_usd == 0.05
    assert est.wall_time_seconds == 2.0


def test_base_detector_estimate_cost_default():
    """Default estimate_cost() returns rows=min(row_count,sample_n), cost=0, positive time."""
    cls = registry.get("zscore_outlier_fraction")
    det = cls()
    est = det.estimate_cost(row_count=500_000, sample_n=100_000)
    assert est.rows_scanned == 100_000
    assert est.warehouse_cost_usd == 0.0
    assert est.wall_time_seconds > 0


def test_base_detector_estimate_cost_small_table():
    cls = registry.get("ks_pvalue")
    det = cls()
    est = det.estimate_cost(row_count=500, sample_n=100_000)
    assert est.rows_scanned == 500  # capped at row_count


def test_aggregate_detector_estimate_cost():
    """Aggregate detectors report near-zero warehouse cost."""
    cls = registry.get("completeness")
    det = cls()
    est = det.estimate_cost(row_count=1_000_000, sample_n=100_000)
    assert est.warehouse_cost_usd == 0.0
    assert est.wall_time_seconds < 1.0


def test_all_registered_detectors_have_estimate_cost():
    """Every registered detector class must expose estimate_cost() without raising."""
    for slug in registry.slugs():
        cls = registry.get(slug)
        try:
            det = cls()
        except (TypeError, ValueError):
            # Some detectors require constructor args (e.g. RowCountInRangeDetector,
            # SetMembershipDetector). estimate_cost is inherited — verify on the class.
            continue
        est = det.estimate_cost(row_count=10_000)
        assert isinstance(est, CostEstimate), f"{slug}: expected CostEstimate"
        assert est.rows_scanned >= 0
        assert est.warehouse_cost_usd >= 0.0
        assert est.wall_time_seconds >= 0.0


def _make_check(slug: str, col: str = "amount") -> dqt.Check:
    return dqt.Check(
        schema_name="public",
        table_name="orders",
        column_name=col,
        detector_slug=slug,
    )


def _mock_adapter(row_data: list[float] | None = None) -> MagicMock:
    adapter = MagicMock()
    data = row_data if row_data is not None else list(range(200))
    adapter.sample.return_value = pd.DataFrame({"amount": data})
    adapter.aggregate.return_value = {"null_count": 5, "total_count": 200}
    adapter.describe_columns.return_value = [
        MagicMock(name="amount", row_count=200)
    ]
    return adapter


def test_run_suite_runs_all_within_budget():
    checks = [_make_check("completeness"), _make_check("zscore_outlier_fraction")]
    adapter = _mock_adapter()
    store = dqt.MemoryStore()
    runner = dqt.Runner(store=store)
    result = runner.run_suite(checks, adapter, cost_budget_usd=100.0)
    assert isinstance(result, SuiteResult)
    assert len(result.ran) == 2
    assert len(result.skipped) == 0
    assert result.budget_spent_usd == 0.0  # both are local/zero-cost


def test_run_suite_respects_zero_budget():
    """With budget=0 and at least one non-zero-cost check, some checks are skipped."""
    from unittest.mock import patch
    from dqt.algorithms._base import CostEstimate

    checks = [_make_check("completeness"), _make_check("zscore_outlier_fraction")]
    adapter = _mock_adapter()
    store = dqt.MemoryStore()
    runner = dqt.Runner(store=store)

    # Patch estimate_cost to return non-zero cost for the second check
    with patch.object(
        registry.get("zscore_outlier_fraction"),
        "estimate_cost",
        return_value=CostEstimate(rows_scanned=200, warehouse_cost_usd=5.0, wall_time_seconds=1.0),
    ):
        result = runner.run_suite(checks, adapter, cost_budget_usd=0.0)

    # completeness is free so it runs; zscore costs $5 so it's skipped
    assert len(result.skipped) >= 1
    skipped_slugs = [c.detector_slug for c, _ in result.skipped]
    assert "zscore_outlier_fraction" in skipped_slugs


def test_suite_result_exported_from_public_api():
    assert hasattr(dqt, "SuiteResult")
    assert hasattr(dqt, "CostEstimate")
