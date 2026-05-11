# packages/dqt/src/dqt/lineage/openlineage.py
# Ref: https://openlineage.io/spec/ — OpenLineage 1.x event schema
# Emits START / COMPLETE / FAIL lifecycle events so dqt integrates with Marquez,
# Datakin, and OpenMetadata without requiring the openlineage-python SDK.
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class RunState(str, Enum):
    START = "START"
    COMPLETE = "COMPLETE"
    FAIL = "FAIL"


@dataclass
class OpenLineageEmitter:
    """Builds OpenLineage events and optionally POSTs them to a transport URL.

    When ``transport`` is ``None``, events are returned from ``emit()`` but
    not sent anywhere — useful for testing and offline collection.

    Example::

        from dqt.lineage.openlineage import OpenLineageEmitter, RunState
        emitter = OpenLineageEmitter(
            producer="dqt/0.3.0",
            transport="http://marquez:5000/api/v1/lineage",
        )
        run_id = str(uuid4())
        emitter.emit(RunState.START, "analytics.orders.iqr_fence", run_id)
        # ... run the check ...
        emitter.emit(RunState.COMPLETE, "analytics.orders.iqr_fence", run_id,
                     outputs=[{"namespace": "dqt", "name": "analytics.orders"}])
    """
    producer: str
    transport: str | None = None
    namespace: str = "dqt"
    _emitted: list[dict[str, Any]] = field(default_factory=list, init=False, repr=False)

    def build_event(
        self,
        state: RunState,
        job_name: str,
        run_id: str,
        event_time: datetime | None = None,
        inputs: list[dict] | None = None,
        outputs: list[dict] | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        if event_time is None:
            event_time = datetime.now(timezone.utc)

        run_facets: dict[str, Any] = {}
        if error_message:
            run_facets["errorMessage"] = {
                "_producer": self.producer,
                "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/ErrorMessageRunFacet.json",
                "message": error_message,
                "programmingLanguage": "Python",
            }

        return {
            "eventType": state.value,
            "eventTime": event_time.isoformat(),
            "producer": self.producer,
            "schemaURL": "https://openlineage.io/spec/1-0-5/OpenLineage.json",
            "run": {
                "runId": run_id,
                "facets": run_facets,
            },
            "job": {
                "namespace": self.namespace,
                "name": job_name,
                "facets": {},
            },
            "inputs": inputs or [],
            "outputs": outputs or [],
        }

    def emit(
        self,
        state: RunState,
        job_name: str,
        run_id: str,
        event_time: datetime | None = None,
        inputs: list[dict] | None = None,
        outputs: list[dict] | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        event = self.build_event(
            state=state, job_name=job_name, run_id=run_id,
            event_time=event_time, inputs=inputs, outputs=outputs,
            error_message=error_message,
        )
        self._emitted.append(event)
        if self.transport:
            body = json.dumps(event).encode()
            req = urllib.request.Request(
                self.transport, data=body,
                headers={"Content-Type": "application/json"}, method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=5):
                    pass
            except Exception:
                pass  # Non-fatal: lineage emission should never break a check run
        return event
