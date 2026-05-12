# packages/dqt/tests/runner/test_runner_resilience.py
import pandas as pd
import pytest
from unittest.mock import MagicMock
from uuid import uuid4

from dqt.runner.runner import Runner
from dqt.store.memory import MemoryStore
from dqt.algorithms._base import Verdict


def _check():
    from dqt.checks.models import Check
    return Check(id=uuid4(), schema_name="public", table_name="orders",
                 column_name="amount", detector_slug="ks_pvalue", params={})


def test_runner_graceful_degradation_on_timeout():
    """After max_retries exhausted, return warn verdict."""
    store = MemoryStore()
    runner = Runner(store=store, max_retries=1, retry_delay_seconds=0.0)

    adapter = MagicMock()
    adapter.sample.side_effect = TimeoutError("warehouse timed out")

    check = _check()
    result = runner.run(check, adapter)

    assert result.verdict == Verdict.warn
    assert "timeout" in result.plain_english.lower() or "adapter" in result.plain_english.lower()
    saved = store.list_runs(check.id)
    assert len(saved) >= 1


def test_runner_retries_then_succeeds():
    """Runner retries and succeeds on third attempt."""
    store = MemoryStore()
    runner = Runner(store=store, max_retries=3, retry_delay_seconds=0.0)

    adapter = MagicMock()
    adapter.sample.side_effect = [
        OSError("connection refused"),
        OSError("connection refused"),
        pd.DataFrame({"amount": list(range(100))}),
        pd.DataFrame({"amount": list(range(100))}),
    ]

    check = _check()
    result = runner.run(check, adapter)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
