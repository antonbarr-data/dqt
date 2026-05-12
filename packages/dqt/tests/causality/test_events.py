# packages/dqt/tests/causality/test_events.py
# Unit tests for EventSource protocol and adapters. No network calls — urllib mocked.
from __future__ import annotations

import datetime
import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from dqt.causality.events import (
    AirflowEventSource,
    DagsterEventSource,
    DbtCloudEventSource,
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


def _make_response(payload: dict) -> MagicMock:
    """Return a mock context-manager that yields a urllib response."""
    body = json.dumps(payload).encode()
    resp = MagicMock()
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


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


# ---------------------------------------------------------------------------
# AirflowEventSource (mocked HTTP)
# ---------------------------------------------------------------------------

def test_airflow_event_source_returns_deploy_events():
    dag_runs_payload = {
        "dag_runs": [
            {
                "dag_run_id": "run_1",
                "execution_date": "2024-01-01T12:00:00Z",
                "state": "success",
            }
        ]
    }
    with patch("urllib.request.urlopen", return_value=_make_response(dag_runs_payload)):
        src = AirflowEventSource(
            base_url="http://airflow.local",
            dag_ids=["my_dag"],
        )
        events = src.get_events(T0, T2)

    assert len(events) == 1
    assert events[0].event_type == "deploy"
    assert events[0].source == "airflow"
    assert events[0].metadata["dag_id"] == "my_dag"


def test_airflow_event_source_empty_dag_runs():
    with patch("urllib.request.urlopen", return_value=_make_response({"dag_runs": []})):
        src = AirflowEventSource("http://airflow.local", dag_ids=["noop_dag"])
        events = src.get_events(T0, T2)
    assert events == []


# ---------------------------------------------------------------------------
# DagsterEventSource (mocked HTTP)
# ---------------------------------------------------------------------------

def test_dagster_event_source_returns_deploy_events():
    gql_response = {
        "data": {
            "pipelineRunsOrError": {
                "results": [
                    {
                        "runId": "abc-123",
                        "pipelineName": "my_pipeline",
                        "status": "SUCCESS",
                        "startTime": T1.timestamp(),
                        "endTime": T1.timestamp() + 60,
                    }
                ]
            }
        }
    }
    with patch("urllib.request.urlopen", return_value=_make_response(gql_response)):
        src = DagsterEventSource(url="http://dagster.local/graphql")
        events = src.get_events(T0, T2)

    assert len(events) == 1
    assert events[0].event_type == "deploy"
    assert events[0].source == "dagster"
    assert events[0].metadata["run_id"] == "abc-123"


def test_dagster_event_source_empty_results():
    gql_response = {"data": {"pipelineRunsOrError": {"results": []}}}
    with patch("urllib.request.urlopen", return_value=_make_response(gql_response)):
        src = DagsterEventSource(url="http://dagster.local/graphql")
        events = src.get_events(T0, T2)
    assert events == []


# ---------------------------------------------------------------------------
# DbtCloudEventSource (mocked HTTP)
# ---------------------------------------------------------------------------

def test_dbt_cloud_event_source_returns_deploy_events():
    api_response = {
        "data": [
            {
                "id": 99,
                "job_id": 7,
                "created_at": "2024-01-01T06:00:00Z",
                "status": 10,
            }
        ]
    }
    with patch("urllib.request.urlopen", return_value=_make_response(api_response)):
        src = DbtCloudEventSource(account_id=1, api_token="tok")
        events = src.get_events(T0, T2)

    assert len(events) == 1
    assert events[0].event_type == "deploy"
    assert events[0].source == "dbt_cloud"
    assert events[0].metadata["job_id"] == 7


def test_dbt_cloud_event_source_filters_by_job_id():
    api_response = {
        "data": [
            {"id": 1, "job_id": 7, "created_at": "2024-01-01T06:00:00Z", "status": 10},
            {"id": 2, "job_id": 8, "created_at": "2024-01-01T07:00:00Z", "status": 10},
        ]
    }
    with patch("urllib.request.urlopen", return_value=_make_response(api_response)):
        src = DbtCloudEventSource(account_id=1, api_token="tok", job_ids=[7])
        events = src.get_events(T0, T2)

    assert len(events) == 1
    assert events[0].metadata["job_id"] == 7


def test_dbt_cloud_event_source_filters_out_of_range():
    api_response = {
        "data": [
            # T3 is after T2 — should be excluded
            {"id": 3, "job_id": 7, "created_at": "2024-01-04T00:00:00Z", "status": 10},
        ]
    }
    with patch("urllib.request.urlopen", return_value=_make_response(api_response)):
        src = DbtCloudEventSource(account_id=1, api_token="tok")
        events = src.get_events(T0, T2)
    assert events == []
