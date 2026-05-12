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


# --- ProofBundle tests ---

def test_save_and_list_proofs():
    from dqt.store.memory import MemoryStore
    from dqt.store.proof import ProofBundle
    from uuid import uuid4

    store = MemoryStore()
    check_id = uuid4()
    run_id = uuid4()
    proof = ProofBundle(
        run_id=run_id, check_id=check_id,
        detector_slug="ks_pvalue", detector_version="1",
        data_hash="a" * 64, row_count=100, commitment="b" * 64,
    )
    store.save_proof(proof)
    proofs = store.list_proofs(check_id)
    assert len(proofs) == 1
    assert proofs[0].commitment == "b" * 64


def test_list_proofs_empty():
    from dqt.store.memory import MemoryStore
    from uuid import uuid4
    store = MemoryStore()
    assert store.list_proofs(uuid4()) == []


# --- query_runs tests ---

def test_query_runs_by_verdict():
    from dqt.store.memory import MemoryStore
    from dqt.store._protocol import RunResult
    from dqt.algorithms._base import Verdict
    from datetime import datetime, timezone
    from uuid import uuid4

    store = MemoryStore()
    check_id = uuid4()
    now = datetime.now(timezone.utc)

    def _run(v):
        return RunResult(
            run_id=uuid4(), check_id=check_id, detector_slug="ks_pvalue",
            detector_version="1", started_at=now, finished_at=now,
            verdict=v, score=0.5 if v == Verdict.pass_ else 0.99,
            plain_english="ok", details={},
        )

    store.save_run(_run(Verdict.pass_))
    store.save_run(_run(Verdict.pass_))
    store.save_run(_run(Verdict.fail))

    fails = store.query_runs(check_id=check_id, verdict=Verdict.fail)
    assert len(fails) == 1
    passes = store.query_runs(check_id=check_id, verdict=Verdict.pass_)
    assert len(passes) == 2
    all_runs = store.query_runs(check_id=check_id)
    assert len(all_runs) == 3


def test_query_runs_no_filters_returns_all():
    from dqt.store.memory import MemoryStore
    from dqt.store._protocol import RunResult
    from dqt.algorithms._base import Verdict
    from datetime import datetime, timezone
    from uuid import uuid4

    store = MemoryStore()
    now = datetime.now(timezone.utc)
    for _ in range(5):
        store.save_run(RunResult(
            run_id=uuid4(), check_id=uuid4(), detector_slug="ks_pvalue",
            detector_version="1", started_at=now, finished_at=now,
            verdict=Verdict.pass_, score=0.1, plain_english="ok", details={},
        ))
    all_runs = store.query_runs(limit=100)
    assert len(all_runs) == 5
