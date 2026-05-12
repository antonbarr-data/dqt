# packages/dqt/tests/runner/test_dry_run.py
import pandas as pd
import pytest
from unittest.mock import MagicMock
from uuid import uuid4

from dqt.runner.runner import Runner
from dqt.store.memory import MemoryStore


def _check_obj():
    from dqt.checks.models import Check
    return Check(
        id=uuid4(),
        schema_name="public",
        table_name="orders",
        column_name="amount",
        detector_slug="ks_pvalue",
        params={},
    )


def test_dry_run_returns_sql_and_cost():
    from dqt.algorithms._base import CostEstimate
    store = MemoryStore()
    runner = Runner(store=store)
    adapter = MagicMock()

    check = _check_obj()
    sql, cost = runner.dry_run(check, adapter)
    assert isinstance(sql, str)
    assert len(sql) > 0
    assert isinstance(cost, CostEstimate)
    assert cost.rows_scanned >= 0


def test_dry_run_does_not_save_to_store():
    store = MemoryStore()
    runner = Runner(store=store)
    adapter = MagicMock()

    check = _check_obj()
    runner.dry_run(check, adapter)
    assert store.list_runs(check.id, limit=100) == []
