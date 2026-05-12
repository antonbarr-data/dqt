# packages/dqt-dagster/tests/test_resources.py
"""Tests for Dagster dqt resource (no dagster dependency required)."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "dqt" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import dqt
from dqt_dagster.resources import DqtResource, DqtAssetCheckFailed, run_dqt_checks


def _make_check(table: str = "orders") -> dqt.Check:
    return dqt.Check(
        schema_name="public",
        table_name=table,
        column_name="amount",
        detector_slug="completeness",
    )


def _make_adapter() -> MagicMock:
    adapter = MagicMock()
    adapter.sample.return_value = pd.DataFrame({"amount": list(range(200))})
    adapter.aggregate.return_value = {"null_count": 0, "total_count": 200}
    adapter.describe_columns.return_value = [MagicMock(name="amount", row_count=200)]
    return adapter


def test_run_dqt_checks_passes_on_clean_data():
    check = _make_check()
    store = dqt.MemoryStore()
    runner = dqt.Runner(store=store)
    adapter = _make_adapter()
    suite = run_dqt_checks([check], runner, adapter)
    assert len(suite.ran) == 1
    assert len(suite.skipped) == 0


def test_run_dqt_checks_raises_on_fail():
    from dqt.algorithms._base import Verdict
    from dqt.runner.runner import SuiteResult
    from dqt.store._protocol import RunResult
    from datetime import datetime, timezone
    check = _make_check()
    store = dqt.MemoryStore()
    runner = dqt.Runner(store=store)

    failing = RunResult(
        check_id=check.id,
        detector_slug="completeness",
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        verdict=Verdict.fail,
        score=1.0,
        plain_english="fail",
    )
    with patch.object(runner, "run_suite") as mock:
        mock.return_value = SuiteResult(ran=[failing], budget_total_usd=10.0)
        with pytest.raises(DqtAssetCheckFailed):
            run_dqt_checks([check], runner, MagicMock())


def test_resource_run_checks_for_filters_by_table():
    chk_orders = _make_check("orders")
    chk_sessions = _make_check("sessions")
    store = dqt.MemoryStore()
    runner = dqt.Runner(store=store)
    adapter = _make_adapter()

    resource = DqtResource(
        runner_factory=lambda: runner,
        adapter_factory=lambda: adapter,
        checks=[chk_orders, chk_sessions],
    )
    suite = resource.run_checks_for("orders")
    # Only 1 check ran — the orders one
    assert len(suite.ran) == 1


def test_resource_run_suite_all_checks():
    chk1 = _make_check("orders")
    chk2 = _make_check("sessions")
    store = dqt.MemoryStore()
    runner = dqt.Runner(store=store)
    adapter = _make_adapter()

    resource = DqtResource(
        runner_factory=lambda: runner,
        adapter_factory=lambda: adapter,
        checks=[chk1, chk2],
    )
    suite = resource.run_suite()
    assert len(suite.ran) == 2


def test_dqt_asset_check_failed_is_exception():
    exc = DqtAssetCheckFailed("completeness failed")
    assert isinstance(exc, Exception)
    assert "completeness" in str(exc)
