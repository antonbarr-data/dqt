# packages/dqt/tests/runner/test_parallel_suite.py
import pandas as pd
import pytest
from unittest.mock import MagicMock
from uuid import uuid4

from dqt.runner.runner import Runner
from dqt.store.memory import MemoryStore


def _checks(n):
    from dqt.checks.models import Check
    return [
        Check(id=uuid4(), schema_name="public", table_name="orders",
              column_name="amount", detector_slug="ks_pvalue", params={})
        for _ in range(n)
    ]


def test_run_suite_parallel_same_count_as_serial():
    def _adapter():
        a = MagicMock()
        a.sample.return_value = pd.DataFrame({"amount": list(range(100))})
        return a

    checks = _checks(4)

    runner_s = Runner(store=MemoryStore())
    result_s = runner_s.run_suite(checks, _adapter(), parallelism=1)

    runner_p = Runner(store=MemoryStore())
    result_p = runner_p.run_suite(checks, _adapter(), parallelism=4)

    assert len(result_s.ran) == len(result_p.ran) == 4


def test_run_suite_parallelism_default_is_1():
    import inspect
    sig = inspect.signature(Runner.run_suite)
    assert "parallelism" in sig.parameters
    assert sig.parameters["parallelism"].default == 1
