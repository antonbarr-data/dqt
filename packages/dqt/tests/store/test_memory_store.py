import uuid
from datetime import datetime, timezone

import pytest

from dqt.algorithms._base import Verdict
from dqt.store._protocol import Incident, RunResult


@pytest.fixture()
def store():
    from dqt.store.memory import MemoryStore
    return MemoryStore()


@pytest.fixture()
def sample_run(store):
    check_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    run = RunResult(
        check_id=check_id,
        detector_slug="completeness",
        started_at=now,
        finished_at=now,
        verdict=Verdict.pass_,
        score=0.99,
        plain_english="99% complete",
    )
    store.save_run(run)
    return run, check_id


def test_save_and_list_run(store, sample_run):
    run, check_id = sample_run
    runs = store.list_runs(check_id)
    assert len(runs) == 1
    assert runs[0].run_id == run.run_id


def test_list_runs_empty(store):
    assert store.list_runs(uuid.uuid4()) == []


def test_list_runs_limit(store):
    check_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    for _ in range(5):
        store.save_run(RunResult(
            check_id=check_id,
            detector_slug="completeness",
            started_at=now,
            finished_at=now,
            verdict=Verdict.pass_,
            score=0.99,
            plain_english="ok",
        ))
    assert len(store.list_runs(check_id, limit=3)) == 3


def test_save_and_list_incident(store, sample_run):
    run, check_id = sample_run
    now = datetime.now(timezone.utc)
    inc = Incident(
        check_id=check_id,
        run_id=run.run_id,
        detector_slug="completeness",
        severity=Verdict.fail,
        opened_at=now,
        score=0.7,
    )
    store.save_incident(inc)
    incidents = store.list_incidents(check_id)
    assert len(incidents) == 1
    assert incidents[0].incident_id == inc.incident_id


def test_list_incidents_by_status(store, sample_run):
    run, check_id = sample_run
    now = datetime.now(timezone.utc)
    store.save_incident(Incident(
        check_id=check_id, run_id=run.run_id, detector_slug="completeness",
        severity=Verdict.warn, opened_at=now, score=0.93, status="open",
    ))
    store.save_incident(Incident(
        check_id=check_id, run_id=run.run_id, detector_slug="completeness",
        severity=Verdict.warn, opened_at=now, score=0.93, status="resolved",
    ))
    assert len(store.list_incidents(check_id, status="open")) == 1
    assert len(store.list_incidents(check_id, status="resolved")) == 1
    assert len(store.list_incidents(check_id)) == 2


def test_implements_results_store_protocol(store):
    from dqt.store._protocol import ResultsStore
    assert isinstance(store, ResultsStore)
