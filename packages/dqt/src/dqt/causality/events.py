# packages/dqt/src/dqt/causality/events.py
# Protocol + concrete adapters for external event sources used to condition causal discovery.
# Ref: Pearl (2009) Causality Ch.3 — conditioning on observed interventions (do-calculus)
from __future__ import annotations

import datetime
import json
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


# ---------------------------------------------------------------------------
# HTTP helper (stdlib only)
# ---------------------------------------------------------------------------

def _http_get(url: str, headers: dict[str, str] | None = None) -> dict:
    """GET url, return parsed JSON. Raises urllib.error.HTTPError on non-2xx."""
    import urllib.request
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req) as resp:  # noqa: S310
        return json.loads(resp.read().decode())


def _http_post(url: str, payload: dict, headers: dict[str, str] | None = None) -> dict:
    """POST JSON payload to url, return parsed JSON."""
    import urllib.request
    data = json.dumps(payload).encode()
    h = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(url, data=data, headers=h, method="POST")
    with urllib.request.urlopen(req) as resp:  # noqa: S310
        return json.loads(resp.read().decode())


def _iso(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Airflow adapter
# ---------------------------------------------------------------------------

class AirflowEventSource:
    """Reads DAG run completions from Airflow REST API v2."""

    def __init__(
        self,
        base_url: str,
        dag_ids: list[str] | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._dag_ids = dag_ids  # None = fetch all DAGs
        self._username = username
        self._password = password

    def _auth_headers(self) -> dict[str, str]:
        if self._username and self._password:
            import base64
            creds = base64.b64encode(f"{self._username}:{self._password}".encode()).decode()
            return {"Authorization": f"Basic {creds}"}
        return {}

    def _dag_list(self) -> list[str]:
        if self._dag_ids is not None:
            return self._dag_ids
        data = _http_get(f"{self._base_url}/api/v2/dags", self._auth_headers())
        return [d["dag_id"] for d in data.get("dags", [])]

    def get_events(self, start: datetime.datetime, end: datetime.datetime) -> list[DeployEvent]:
        try:
            import urllib.request  # noqa: F401 — ensure stdlib available (it always is)
        except ImportError as exc:
            raise ImportError("urllib.request is unavailable (unexpected)") from exc

        events: list[DeployEvent] = []
        headers = self._auth_headers()
        for dag_id in self._dag_list():
            url = (
                f"{self._base_url}/api/v2/dags/{dag_id}/dagRuns"
                f"?execution_date_gte={_iso(start)}&execution_date_lte={_iso(end)}&state=success"
            )
            data = _http_get(url, headers)
            for run in data.get("dag_runs", []):
                ts_str = run.get("execution_date") or run.get("logical_date", "")
                try:
                    ts = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    ts = ts.replace(tzinfo=None)
                except (ValueError, AttributeError):
                    ts = start
                events.append(DeployEvent(
                    event_time=ts,
                    event_type="deploy",
                    source="airflow",
                    description=f"Airflow DAG {dag_id} run {run.get('dag_run_id', '')}",
                    metadata={"dag_id": dag_id, "run_id": run.get("dag_run_id", "")},
                ))
        return events


# ---------------------------------------------------------------------------
# Dagster adapter
# ---------------------------------------------------------------------------

_DAGSTER_GQL = """
query PipelineRuns($after: String, $before: String, $names: [String!]) {
  pipelineRunsOrError(
    filter: {
      statuses: [SUCCESS]
      pipelineNames: $names
      updatedAfter: $after
      updatedBefore: $before
    }
  ) {
    ... on PipelineRuns {
      results {
        runId
        pipelineName
        status
        startTime
        endTime
      }
    }
  }
}
"""


class DagsterEventSource:
    """Reads pipeline run completions from Dagster GraphQL API."""

    def __init__(
        self,
        url: str,
        pipeline_names: list[str] | None = None,
        api_key: str | None = None,
    ) -> None:
        self._url = url
        self._pipeline_names = pipeline_names
        self._api_key = api_key

    def _auth_headers(self) -> dict[str, str]:
        if self._api_key:
            return {"Dagster-Cloud-Api-Token": self._api_key}
        return {}

    def get_events(self, start: datetime.datetime, end: datetime.datetime) -> list[DeployEvent]:
        payload = {
            "query": _DAGSTER_GQL,
            "variables": {
                "after": _iso(start),
                "before": _iso(end),
                "names": self._pipeline_names,
            },
        }
        data = _http_post(self._url, payload, self._auth_headers())
        runs_data = (
            data.get("data", {})
            .get("pipelineRunsOrError", {})
            .get("results", [])
        )
        events: list[DeployEvent] = []
        for run in runs_data:
            raw_ts = run.get("startTime")
            try:
                ts = datetime.datetime.fromtimestamp(float(raw_ts))
            except (TypeError, ValueError):
                ts = start
            events.append(DeployEvent(
                event_time=ts,
                event_type="deploy",
                source="dagster",
                description=f"Dagster pipeline {run.get('pipelineName', '')} run {run.get('runId', '')}",
                metadata={"run_id": run.get("runId", ""), "pipeline": run.get("pipelineName", "")},
            ))
        return events


# ---------------------------------------------------------------------------
# dbt Cloud adapter
# ---------------------------------------------------------------------------

class DbtCloudEventSource:
    """Reads dbt Cloud job runs via dbt Cloud API v2."""

    _BASE = "https://cloud.getdbt.com"

    def __init__(
        self,
        account_id: int,
        api_token: str,
        job_ids: list[int] | None = None,
    ) -> None:
        self._account_id = account_id
        self._api_token = api_token
        self._job_ids = job_ids

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Token {self._api_token}"}

    def get_events(self, start: datetime.datetime, end: datetime.datetime) -> list[DeployEvent]:
        # status=10 → success in dbt Cloud
        url = f"{self._BASE}/api/v2/accounts/{self._account_id}/runs/?status=10&limit=200"
        data = _http_get(url, self._auth_headers())
        events: list[DeployEvent] = []
        for run in data.get("data", []):
            if self._job_ids and run.get("job_id") not in self._job_ids:
                continue
            ts_str = run.get("created_at", "")
            try:
                ts = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                ts = ts.replace(tzinfo=None)
            except (ValueError, AttributeError):
                ts = start
            if not (start <= ts <= end):
                continue
            events.append(DeployEvent(
                event_time=ts,
                event_type="deploy",
                source="dbt_cloud",
                description=f"dbt Cloud job {run.get('job_id', '')} run {run.get('id', '')}",
                metadata={"run_id": run.get("id", ""), "job_id": run.get("job_id", "")},
            ))
        return events
