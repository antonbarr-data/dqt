# packages/dqt/tests/lineage/test_openlineage.py
from datetime import datetime, timezone
from uuid import uuid4

import pytest


@pytest.mark.unit
def test_emit_start_and_complete():
    """START then COMPLETE events round-trip correctly with no transport."""
    from dqt.lineage.openlineage import OpenLineageEmitter, RunState

    emitter = OpenLineageEmitter(producer="dqt/test", transport=None)
    run_id = str(uuid4())
    now = datetime.now(timezone.utc)

    start_event = emitter.emit(
        state=RunState.START,
        job_name="analytics.orders.iqr_fence",
        run_id=run_id,
        event_time=now,
        inputs=[{"namespace": "dqt", "name": "analytics.orders"}],
    )
    assert start_event["eventType"] == "START"
    assert start_event["run"]["runId"] == run_id
    assert len(start_event["inputs"]) == 1

    complete_event = emitter.emit(
        state=RunState.COMPLETE,
        job_name="analytics.orders.iqr_fence",
        run_id=run_id,
        event_time=now,
        outputs=[{"namespace": "dqt", "name": "analytics.orders"}],
    )
    assert complete_event["eventType"] == "COMPLETE"
    assert len(complete_event["outputs"]) == 1

    assert len(emitter._emitted) == 2


@pytest.mark.unit
def test_emit_fail_event():
    """FAIL event includes error message and is appended to _emitted."""
    from dqt.lineage.openlineage import OpenLineageEmitter, RunState

    emitter = OpenLineageEmitter(producer="dqt/test", transport=None)
    error_msg = "12% of values outside IQR fences — verdict: fail"
    event = emitter.emit(
        state=RunState.FAIL,
        job_name="analytics.orders.iqr_fence",
        run_id=str(uuid4()),
        event_time=datetime.now(timezone.utc),
        error_message=error_msg,
    )
    assert event["eventType"] == "FAIL"
    assert "errorMessage" in event.get("run", {}).get("facets", {})
    assert event["run"]["facets"]["errorMessage"]["message"] == error_msg
    assert len(emitter._emitted) == 1
