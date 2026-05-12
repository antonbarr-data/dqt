# packages/dqt/tests/causality/test_events.py
# Unit tests for EventSource protocol and adapters. No network calls — urllib mocked.
from __future__ import annotations

import datetime

import numpy as np
import pandas as pd

from dqt.causality.events import (
    DeployEvent,
    EventSource,
    InMemoryEventSource,
    NullEventSource,
)
from dqt.causality.granger import GrangerReport, granger_pairwise


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

T0 = datetime.datetime(2024, 1, 1, 0, 0, 0)
T1 = datetime.datetime(2024, 1, 2, 0, 0, 0)
T2 = datetime.datetime(2024, 1, 3, 0, 0, 0)
T3 = datetime.datetime(2024, 1, 4, 0, 0, 0)


def _granger_df(n: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    x = rng.normal(0, 1, n)
    y = np.roll(x, 1) + rng.normal(0, 0.1, n)
    return pd.DataFrame({"x": x, "y": y})


# ---------------------------------------------------------------------------
# NullEventSource
# ---------------------------------------------------------------------------

def test_null_event_source_returns_empty():
    src = NullEventSource()
    result = src.get_events(T0, T2)
    assert result == []


def test_null_event_source_is_event_source_protocol():
    assert isinstance(NullEventSource(), EventSource)


# ---------------------------------------------------------------------------
# InMemoryEventSource
# ---------------------------------------------------------------------------

def test_in_memory_event_source_filters_by_time():
    src = InMemoryEventSource()
    src.add(DeployEvent(event_time=T0, event_type="deploy", source="manual", description="before"))
    src.add(DeployEvent(event_time=T1, event_type="deploy", source="manual", description="in range"))
    src.add(DeployEvent(event_time=T3, event_type="deploy", source="manual", description="after"))

    result = src.get_events(T1, T2)
    assert len(result) == 1
    assert result[0].description == "in range"


def test_in_memory_event_source_inclusive_boundaries():
    src = InMemoryEventSource([
        DeployEvent(event_time=T0, event_type="deploy", source="manual"),
        DeployEvent(event_time=T2, event_type="deploy", source="manual"),
    ])
    result = src.get_events(T0, T2)
    assert len(result) == 2


def test_in_memory_event_source_is_event_source_protocol():
    assert isinstance(InMemoryEventSource(), EventSource)


def test_in_memory_event_source_init_with_list():
    events = [DeployEvent(event_time=T1, event_type="deploy", source="manual")]
    src = InMemoryEventSource(events)
    assert len(src.get_events(T0, T2)) == 1


# ---------------------------------------------------------------------------
# GrangerReport — metadata field
# ---------------------------------------------------------------------------

def test_granger_report_has_metadata_field():
    report = GrangerReport()
    assert hasattr(report, "metadata")
    assert isinstance(report.metadata, dict)


def test_granger_report_metadata_default_empty():
    report = GrangerReport()
    assert report.metadata == {}


# ---------------------------------------------------------------------------
# granger_pairwise — event annotation
# ---------------------------------------------------------------------------

def test_granger_annotates_when_events_overlap():
    df = _granger_df()
    src = InMemoryEventSource([
        DeployEvent(
            event_time=T1,
            event_type="deploy",
            source="manual",
            description="prod deploy v2.3",
        )
    ])
    report = granger_pairwise(df, max_lag=2, events=src, period=(T0, T2))
    assert "confounded_by_events" in report.metadata
    assert len(report.metadata["confounded_by_events"]) == 1
    assert "prod deploy v2.3" in report.metadata["confounded_by_events"][0]


def test_granger_no_annotation_when_no_events_in_range():
    df = _granger_df()
    src = InMemoryEventSource([
        DeployEvent(event_time=T3, event_type="deploy", source="manual", description="future deploy"),
    ])
    report = granger_pairwise(df, max_lag=2, events=src, period=(T0, T2))
    assert "confounded_by_events" not in report.metadata


def test_granger_no_annotation_when_events_is_none():
    df = _granger_df()
    report = granger_pairwise(df, max_lag=2)
    assert "confounded_by_events" not in report.metadata


def test_granger_no_annotation_when_period_is_none():
    df = _granger_df()
    src = InMemoryEventSource([
        DeployEvent(event_time=T1, event_type="deploy", source="manual"),
    ])
    # events provided but no period — annotation should not error, just skip
    report = granger_pairwise(df, max_lag=2, events=src, period=None)
    assert "confounded_by_events" not in report.metadata


