# packages/dqt/src/dqt/causality/events.py
# Protocol + concrete adapters for external event sources used to condition causal discovery.
# Ref: Pearl (2009) Causality Ch.3 — conditioning on observed interventions (do-calculus)
#
# InMemoryEventSource and NullEventSource are the supported implementations.
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class DeployEvent:
    event_time: datetime.datetime
    event_type: str   # "deploy" | "migration" | "campaign" | "incident" | "other"
    source: str       # "airflow" | "dagster" | "dbt_cloud" | "manual"
    description: str = ""
    metadata: dict = field(default_factory=dict)


@runtime_checkable
class EventSource(Protocol):
    def get_events(
        self,
        start: datetime.datetime,
        end: datetime.datetime,
    ) -> list[DeployEvent]: ...


class NullEventSource:
    """Always returns no events. Default when no source is configured."""

    def get_events(self, start: datetime.datetime, end: datetime.datetime) -> list[DeployEvent]:
        return []


class InMemoryEventSource:
    """Stores events in a list; useful for testing and notebooks."""

    def __init__(self, events: list[DeployEvent] | None = None) -> None:
        self._events: list[DeployEvent] = list(events) if events else []

    def add(self, event: DeployEvent) -> None:
        self._events.append(event)

    def get_events(self, start: datetime.datetime, end: datetime.datetime) -> list[DeployEvent]:
        return [e for e in self._events if start <= e.event_time <= end]
