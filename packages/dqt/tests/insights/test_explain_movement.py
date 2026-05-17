# packages/dqt/tests/insights/test_explain_movement.py
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from dqt.store.memory import MemoryStore
from dqt.store._protocol import RunResult, MetricRun
from dqt.algorithms._base import Verdict
from dqt.insights.explain import explain_movement


def _now():
    return datetime.now(timezone.utc)


def _seed_metric_runs(store: MemoryStore, fqn: str, n: int = 30) -> None:
    rng = np.random.default_rng(0)
    for i in range(n):
        store.save_metric_run(MetricRun(
            metric_fqn=fqn,
            run_at=_now() - timedelta(days=n - i),
            value=float(rng.normal(100, 5)),
            verdict="pass",
        ))


def test_explain_movement_returns_explanation():
    store = MemoryStore()
    _seed_metric_runs(store, "test.revenue")
    result = explain_movement("test.revenue", (_now() - timedelta(days=7), _now()), store=store)
    assert result.metric_fqn == "test.revenue"
    assert result.primary_channel in ("data", "business", "mixed")
    assert isinstance(result.summary_paragraph, str) and result.summary_paragraph


def test_explain_movement_data_issue_detected():
    store = MemoryStore()
    _seed_metric_runs(store, "test.revenue")
    store.save_run(RunResult(
        check_id=uuid4(), detector_slug="null_fraction",
        started_at=_now(), finished_at=_now(),
        verdict=Verdict.fail, score=0.15,
        plain_english="15% null", details={},
    ))
    result = explain_movement("test.revenue", (_now() - timedelta(minutes=5), _now()), store=store)
    assert len(result.data_issues) >= 1
    assert result.data_issues[0].verdict == "fail"


def test_explain_movement_primary_channel_data_when_only_issues():
    store = MemoryStore()
    store.save_run(RunResult(
        check_id=uuid4(), detector_slug="null_fraction",
        started_at=_now(), finished_at=_now(),
        verdict=Verdict.fail, score=0.20,
        plain_english="20% null", details={},
    ))
    result = explain_movement("test.m", (_now() - timedelta(minutes=5), _now()), store=store)
    assert result.primary_channel in ("data", "mixed")


def test_explain_movement_no_issues_or_drivers():
    store = MemoryStore()
    result = explain_movement("test.m", (_now() - timedelta(hours=1), _now()), store=store)
    assert result.data_issues == []
    assert result.summary_paragraph  # template fallback always produces text


def test_explain_movement_panel_drives_channel_b():
    rng = np.random.default_rng(42)
    n = 60
    ad = rng.normal(100, 10, n)
    rev = np.roll(ad, 1) * 1.5 + rng.normal(0, 5, n)
    rev[0] = rev[1]
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    panel = pd.DataFrame({"revenue": rev, "ad_spend": ad}, index=idx)
    store = MemoryStore()
    result = explain_movement(
        "revenue",
        (idx[0].to_pydatetime(), idx[-1].to_pydatetime()),
        store=store,
        panel=panel,
    )
    assert isinstance(result.business_drivers, list)
