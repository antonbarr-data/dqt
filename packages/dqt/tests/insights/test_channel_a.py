from datetime import datetime, timezone, timedelta
from uuid import uuid4
from dqt.store.memory import MemoryStore
from dqt.store._protocol import RunResult
from dqt.algorithms._base import Verdict
from dqt.insights.channel_a import scan


def _now():
    return datetime.now(timezone.utc)


def _make_run(verdict: Verdict, score: float, store: MemoryStore) -> None:
    store.save_run(RunResult(
        check_id=uuid4(),
        detector_slug="null_fraction",
        started_at=_now(),
        finished_at=_now(),
        verdict=verdict,
        score=score,
        plain_english=f"null fraction is {score:.0%}",
        details={"null_count": int(score * 1000), "total_count": 1000},
    ))


def test_scan_returns_empty_when_no_issues():
    store = MemoryStore()
    issues = scan("m", _now() - timedelta(hours=1), _now(), store)
    assert issues == []


def test_scan_returns_fail_issue():
    store = MemoryStore()
    _make_run(Verdict.fail, 0.15, store)
    issues = scan("m", _now() - timedelta(minutes=5), _now(), store)
    assert len(issues) == 1
    assert issues[0].verdict == "fail"
    assert issues[0].contribution_low < issues[0].contribution_high


def test_scan_excludes_passes():
    store = MemoryStore()
    _make_run(Verdict.pass_, 0.001, store)
    issues = scan("m", _now() - timedelta(minutes=5), _now(), store)
    assert issues == []


def test_scan_orders_by_contribution_descending():
    store = MemoryStore()
    _make_run(Verdict.warn, 0.03, store)
    _make_run(Verdict.fail, 0.20, store)
    issues = scan("m", _now() - timedelta(minutes=5), _now(), store)
    assert issues[0].verdict == "fail"   # fail ranked first (higher contribution)
