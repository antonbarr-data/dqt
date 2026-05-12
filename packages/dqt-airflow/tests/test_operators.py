# packages/dqt-airflow/tests/test_operators.py
"""Tests for Airflow dqt operators (no airflow dependency required)."""
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "dqt" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import dqt
from dqt_airflow.operators import DqtCheckOperator, DqtSuiteOperator, _DqtCheckFailed


def _make_check(table: str = "orders") -> dqt.Check:
    return dqt.Check(
        schema_name="public",
        table_name=table,
        column_name="amount",
        detector_slug="completeness",
    )


def _make_adapter(null_count: int = 0) -> MagicMock:
    adapter = MagicMock()
    adapter.sample.return_value = pd.DataFrame({"amount": list(range(200))})
    adapter.aggregate.return_value = {"null_count": null_count, "total_count": 200}
    adapter.describe_columns.return_value = [MagicMock(name="amount", row_count=200)]
    return adapter


def _make_runner_and_store() -> tuple[dqt.Runner, dqt.MemoryStore]:
    store = dqt.MemoryStore()
    runner = dqt.Runner(store=store)
    return runner, store


def test_check_operator_passes_on_clean_data():
    check = _make_check()
    runner, _ = _make_runner_and_store()
    adapter = _make_adapter(null_count=0)

    op = DqtCheckOperator(
        task_id="dqt_check",
        check_factory=lambda: check,
        runner_factory=lambda: runner,
        adapter_factory=lambda: adapter,
    )
    result = op.execute(context={})
    assert result["verdict"] == "pass"
    assert result["detector_slug"] == "completeness"


def test_check_operator_raises_on_fail():
    from unittest.mock import patch
    from dqt.algorithms._base import Verdict, DetectorResult
    check = _make_check()
    runner, _ = _make_runner_and_store()
    adapter = _make_adapter(null_count=200)  # 100% null → fail

    op = DqtCheckOperator(
        task_id="dqt_check",
        check_factory=lambda: check,
        runner_factory=lambda: runner,
        adapter_factory=lambda: adapter,
    )
    # Patch the runner to return a failing result
    with patch.object(runner, "run") as mock_run:
        from dqt.store._protocol import RunResult
        from datetime import datetime, timezone
        from uuid import uuid4
        mock_run.return_value = RunResult(
            check_id=check.id,
            detector_slug="completeness",
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            verdict=Verdict.fail,
            score=1.0,
            plain_english="100% null",
        )
        with pytest.raises(_DqtCheckFailed):
            op.execute(context={})


def test_suite_operator_passes_on_clean_data():
    checks = [_make_check("orders"), _make_check("sessions")]
    runner, _ = _make_runner_and_store()
    adapter = _make_adapter(null_count=0)

    op = DqtSuiteOperator(
        task_id="dqt_suite",
        checks_factory=lambda: checks,
        runner_factory=lambda: runner,
        adapter_factory=lambda: adapter,
    )
    result = op.execute(context={})
    assert result["n_ran"] == 2
    assert result["n_fail"] == 0


def test_suite_operator_raises_when_any_check_fails():
    check = _make_check("orders")
    runner, _ = _make_runner_and_store()
    adapter = _make_adapter()

    op = DqtSuiteOperator(
        task_id="dqt_suite",
        checks_factory=lambda: [check],
        runner_factory=lambda: runner,
        adapter_factory=lambda: adapter,
    )
    from unittest.mock import patch
    from dqt.algorithms._base import Verdict
    from dqt.runner.runner import SuiteResult
    from dqt.store._protocol import RunResult
    from datetime import datetime, timezone

    failing_run = RunResult(
        check_id=check.id,
        detector_slug="completeness",
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        verdict=Verdict.fail,
        score=1.0,
        plain_english="fail",
    )
    with patch.object(runner, "run_suite") as mock_suite:
        mock_suite.return_value = SuiteResult(ran=[failing_run], budget_total_usd=10.0)
        with pytest.raises(_DqtCheckFailed):
            op.execute(context={})


def test_provider_info():
    from dqt_airflow import get_provider_info
    info = get_provider_info()
    assert info["package-name"] == "airflow-providers-dqt"
    assert "versions" in info
