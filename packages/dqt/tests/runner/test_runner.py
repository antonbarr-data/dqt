import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import Verdict
from dqt.checks.models import BaselineConfig, Check, CheckFilter, CheckScope
from dqt.store.memory import MemoryStore


def make_adapter(
    sample_df: pd.DataFrame | None = None,
    aggregate_result: dict | None = None,
) -> MagicMock:
    adapter = MagicMock()
    if sample_df is not None:
        adapter.sample.return_value = sample_df
    if aggregate_result is not None:
        adapter.aggregate.return_value = aggregate_result
    return adapter


def completeness_check() -> Check:
    return Check(
        schema_name="public",
        table_name="orders",
        column_name="amount",
        detector_slug="completeness",
    )


def ks_check() -> Check:
    return Check(
        schema_name="public",
        table_name="orders",
        column_name="value",
        detector_slug="ks_pvalue",
    )


@pytest.fixture(autouse=True)
def _register_detectors():
    import dqt.algorithms.basic
    import dqt.algorithms.drift


def test_runner_run_aggregate_detector_pass():
    from dqt.runner.runner import Runner
    store = MemoryStore()
    runner = Runner(store=store)
    adapter = make_adapter(aggregate_result={"null_count": 5, "total_count": 1000})
    check = completeness_check()
    runner.fit(check, adapter)
    result = runner.run(check, adapter)
    assert result.verdict == Verdict.pass_
    assert result.detector_slug == "completeness"
    runs = store.list_runs(check.id)
    assert len(runs) == 1
    assert runs[0].run_id == result.run_id


def test_runner_run_creates_incident_on_fail():
    from dqt.runner.runner import Runner
    store = MemoryStore()
    runner = Runner(store=store)
    adapter = make_adapter(aggregate_result={"null_count": 150, "total_count": 1000})
    check = completeness_check()
    runner.fit(check, adapter)
    result = runner.run(check, adapter)
    assert result.verdict == Verdict.fail
    incidents = store.list_incidents(check.id)
    assert len(incidents) == 1
    assert incidents[0].severity == Verdict.fail


def test_runner_run_creates_incident_on_warn():
    from dqt.runner.runner import Runner
    store = MemoryStore()
    runner = Runner(store=store)
    adapter = make_adapter(aggregate_result={"null_count": 60, "total_count": 1000})
    check = completeness_check()
    runner.fit(check, adapter)
    result = runner.run(check, adapter)
    assert result.verdict == Verdict.warn
    incidents = store.list_incidents(check.id)
    assert len(incidents) == 1


def test_runner_no_incident_on_pass():
    from dqt.runner.runner import Runner
    store = MemoryStore()
    runner = Runner(store=store)
    adapter = make_adapter(aggregate_result={"null_count": 2, "total_count": 1000})
    check = completeness_check()
    runner.fit(check, adapter)
    runner.run(check, adapter)
    assert store.list_incidents(check.id) == []


def test_runner_run_sample_detector():
    from dqt.runner.runner import Runner
    rng = np.random.default_rng(42)
    ref_df = pd.DataFrame({"value": rng.normal(10, 2, 1000)})
    curr_df = pd.DataFrame({"value": rng.normal(10.1, 2, 1000)})
    store = MemoryStore()
    runner = Runner(store=store)
    adapter = make_adapter(sample_df=ref_df)
    check = ks_check()
    runner.fit(check, adapter)
    adapter.sample.return_value = curr_df
    result = runner.run(check, adapter)
    assert result.verdict == Verdict.pass_


def test_runner_auto_refits_if_no_state():
    from dqt.runner.runner import Runner
    store = MemoryStore()
    runner = Runner(store=store)
    adapter = make_adapter(aggregate_result={"null_count": 5, "total_count": 1000})
    check = completeness_check()
    result = runner.run(check, adapter)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    assert adapter.aggregate.call_count >= 2


def test_runner_uses_check_sample_n():
    from dqt.runner.runner import Runner
    rng = np.random.default_rng(42)
    ref_df = pd.DataFrame({"value": rng.normal(10, 2, 500)})
    store = MemoryStore()
    runner = Runner(store=store)
    adapter = make_adapter(sample_df=ref_df)
    check = ks_check()
    check.sample_n = 50_000
    runner.fit(check, adapter)
    adapter.sample.assert_called_with("public", "orders", 50_000)


def test_runner_sampling_pct_overrides_sample_n():
    """sampling_pct is passed through to adapter.sample as a kwarg hint."""
    from dqt.runner.runner import Runner
    rng = np.random.default_rng(42)
    ref_df = pd.DataFrame({"value": rng.normal(10, 2, 500)})
    store = MemoryStore()
    runner = Runner(store=store)
    adapter = make_adapter(sample_df=ref_df)
    check = ks_check()
    check.sampling_pct = 5.0   # 5% sampling
    runner.fit(check, adapter)
    # adapter.sample should have been called with sampling_pct kwarg
    call_kwargs = adapter.sample.call_args
    assert call_kwargs is not None
    # sampling_pct should appear as a keyword argument
    assert call_kwargs.kwargs.get("sampling_pct") == 5.0 or (
        len(call_kwargs.args) >= 4 and call_kwargs.args[3] == 5.0
    )


def test_runner_scope_incremental_passes_to_adapter():
    """Incremental scope is forwarded to adapter.sample."""
    from dqt.runner.runner import Runner
    rng = np.random.default_rng(42)
    ref_df = pd.DataFrame({"value": rng.normal(10, 2, 500)})
    store = MemoryStore()
    runner = Runner(store=store)
    adapter = make_adapter(sample_df=ref_df)
    check = ks_check()
    check.scope = CheckScope(mode="incremental", key_col="created_at", since="2024-01-01")
    runner.fit(check, adapter)
    call_kwargs = adapter.sample.call_args
    # scope should be forwarded
    assert call_kwargs.kwargs.get("scope") is not None or call_kwargs.kwargs.get("key_col") is not None


def test_runner_filters_passed_to_adapter():
    """Column filters are forwarded to adapter.sample."""
    from dqt.runner.runner import Runner
    rng = np.random.default_rng(42)
    ref_df = pd.DataFrame({"value": rng.normal(10, 2, 500)})
    store = MemoryStore()
    runner = Runner(store=store)
    adapter = make_adapter(sample_df=ref_df)
    check = ks_check()
    check.filters = [CheckFilter(col="status", values=["active"])]
    runner.fit(check, adapter)
    call_kwargs = adapter.sample.call_args
    assert call_kwargs.kwargs.get("filters") is not None


def test_power_warning_injected_below_min_n(fake_adapter):
    """When N < min_recommended_n, plain_english includes a power warning."""
    from dqt.runner.runner import Runner

    # wasserstein_1 has min_recommended_n=500; fake_adapter returns 10 rows
    check = Check(
        schema_name="s", table_name="t", column_name="val",
        detector_slug="wasserstein_1",
    )
    store = MemoryStore()
    runner = Runner(store)
    result = runner.run(check, fake_adapter)
    assert "[low-power:" in result.plain_english, (
        f"Expected low-power prefix, got: {result.plain_english!r}"
    )
    assert "N=10" in result.plain_english


def test_degenerate_distribution_skips_outlier_detection():
    """Runner emits degenerate_distribution_detected for >90% null columns."""
    from dqt.runner.runner import Runner

    class _SparseAdapter:
        def sample(self, schema, table, n=100_000, **kwargs):
            vals = [float("nan")] * 95 + list(np.random.default_rng(0).normal(0, 1, 5))
            return pd.DataFrame({"val": vals})
        def aggregate(self, schema, table, exprs):
            return {e.name: 0.0 for e in exprs}
        def list_schemas(self):
            return ["s"]
        def list_tables(self, schema):
            return ["t"]
        def describe_columns(self, schema, table):
            return []
        def health_check(self):
            from dqt.adapters._protocol import HealthCheckResult
            return HealthCheckResult(steps=[])

    check = Check(
        schema_name="s", table_name="t", column_name="val",
        detector_slug="iqr_fence",
    )
    store = MemoryStore()
    runner = Runner(store)
    result = runner.run(check, _SparseAdapter())
    assert "degenerate" in result.plain_english.lower()
    assert result.verdict == Verdict.warn
