# packages/dqt-dbt/tests/test_dbt_callback.py
"""Tests for dbt-dqt callback."""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest

# Add dqt library to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "dqt" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import dqt
from dqt_dbt.callback import DbtRunResult, _load_success_models, run_checks_for_dbt_run


def _make_run_results(model_names: list[str], status: str = "success") -> dict:
    return {
        "results": [
            {"unique_id": f"model.myproject.{name}", "status": status}
            for name in model_names
        ]
    }


def _make_check(table: str) -> dqt.Check:
    return dqt.Check(
        schema_name="public",
        table_name=table,
        column_name="amount",
        detector_slug="completeness",
    )


def _mock_runner(store: dqt.MemoryStore) -> dqt.Runner:
    import pandas as pd
    runner = dqt.Runner(store=store)
    return runner


def test_load_success_models_from_json(tmp_path):
    rr = _make_run_results(["orders", "sessions"])
    p = tmp_path / "run_results.json"
    p.write_text(json.dumps(rr))
    models = _load_success_models(p)
    assert set(models) == {"orders", "sessions"}


def test_load_success_models_ignores_failed(tmp_path):
    rr = {
        "results": [
            {"unique_id": "model.proj.orders", "status": "success"},
            {"unique_id": "model.proj.sessions", "status": "error"},
        ]
    }
    p = tmp_path / "run_results.json"
    p.write_text(json.dumps(rr))
    models = _load_success_models(p)
    assert models == ["orders"]


def test_run_checks_filters_to_matching_models(tmp_path):
    import pandas as pd
    rr = _make_run_results(["orders"])
    (tmp_path / "run_results.json").write_text(json.dumps(rr))

    chk_orders = _make_check("orders")
    chk_sessions = _make_check("sessions")  # not in dbt run

    adapter = MagicMock()
    adapter.sample.return_value = pd.DataFrame({"amount": list(range(200))})
    adapter.aggregate.return_value = {"null_count": 0, "total_count": 200}
    adapter.describe_columns.return_value = [MagicMock(name="amount", row_count=200)]

    store = dqt.MemoryStore()
    runner = dqt.Runner(store=store)

    result = run_checks_for_dbt_run(
        runner=runner,
        adapter=adapter,
        checks=[chk_orders, chk_sessions],
        run_results_path=tmp_path / "run_results.json",
    )

    assert isinstance(result, DbtRunResult)
    assert chk_orders in result.matched_checks
    assert chk_sessions in result.unmatched_checks
    assert len(result.suite.ran) == 1


def test_run_checks_raises_when_file_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_checks_for_dbt_run(
            runner=MagicMock(),
            adapter=MagicMock(),
            checks=[],
            run_results_path=tmp_path / "nonexistent.json",
        )


def test_run_all_when_file_missing_and_flag_set(tmp_path):
    import pandas as pd
    chk = _make_check("orders")
    adapter = MagicMock()
    adapter.sample.return_value = pd.DataFrame({"amount": list(range(200))})
    adapter.aggregate.return_value = {"null_count": 0, "total_count": 200}
    adapter.describe_columns.return_value = [MagicMock(name="amount", row_count=200)]

    store = dqt.MemoryStore()
    runner = dqt.Runner(store=store)

    result = run_checks_for_dbt_run(
        runner=runner,
        adapter=adapter,
        checks=[chk],
        run_results_path=tmp_path / "nonexistent.json",
        run_all_on_missing_results=True,
    )
    assert len(result.matched_checks) == 1
    assert len(result.suite.ran) == 1
