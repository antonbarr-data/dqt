# packages/dqt/src/dqt/dashboard/app.py
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

if TYPE_CHECKING:
    from dqt.store._protocol import ResultsStore

_TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def build_app(store: "ResultsStore") -> FastAPI:
    app = FastAPI(title="dqt dashboard", docs_url=None, redoc_url=None)

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        runs = _get_recent_runs(store)
        return _TEMPLATES.TemplateResponse(
            request, "index.html", {"runs": runs, "title": "dqt", "active": "checks"}
        )

    @app.get("/checks/{check_id}", response_class=HTMLResponse)
    async def check_detail(request: Request, check_id: str):
        runs = _get_runs_for_check(store, check_id)
        latest = runs[0] if runs else None
        return _TEMPLATES.TemplateResponse(
            request,
            "check.html",
            {
                "check_id": check_id,
                "runs": runs,
                "latest": latest,
                "title": f"dqt — {check_id}",
                "active": "checks",
            },
        )

    @app.get("/profile", response_class=HTMLResponse)
    async def profile_list(request: Request):
        reports = _get_profile_reports(store)
        return _TEMPLATES.TemplateResponse(
            request, "profile.html", {"reports": reports, "title": "dqt — profile", "active": "profile"}
        )

    @app.get("/profile/{dataset_name}", response_class=HTMLResponse)
    async def profile_detail(request: Request, dataset_name: str):
        report = _get_profile_report_by_name(store, dataset_name)
        return _TEMPLATES.TemplateResponse(
            request,
            "profile_detail.html",
            {
                "report": report,
                "dataset_name": dataset_name,
                "title": f"dqt — profile — {dataset_name}",
                "active": "profile",
            },
        )

    @app.get("/causality", response_class=HTMLResponse)
    async def causality(request: Request):
        reports = _get_causality_reports(store)
        return _TEMPLATES.TemplateResponse(
            request,
            "causality.html",
            {"reports": reports, "title": "dqt — causality", "active": "causality"},
        )

    @app.get("/incidents", response_class=HTMLResponse)
    async def incidents_list(request: Request):
        incidents = _get_all_incidents(store)
        return _TEMPLATES.TemplateResponse(
            request, "incidents.html",
            {"incidents": incidents, "title": "dqt — incidents", "active": "incidents"},
        )

    @app.get("/incidents/{check_id}", response_class=HTMLResponse)
    async def incident_detail(request: Request, check_id: str):
        detail = _get_incident_detail(store, check_id)
        return _TEMPLATES.TemplateResponse(
            request, "incident_detail.html",
            {
                "check_id": check_id,
                "detail": detail,
                "title": f"dqt — incident — {check_id}",
                "active": "incidents",
            },
        )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


def _get_recent_runs(store: "ResultsStore") -> list[dict]:
    """Return the latest run for each known check, sorted by check_id string.

    ResultsStore.list_runs requires a check_id UUID; there is no list_check_ids()
    on the protocol yet. For MemoryStore we read the internal index directly.
    Non-MemoryStore backends return an empty index until list_check_ids() is added.
    """
    # _runs: dict[UUID, list[RunResult]] on MemoryStore — read-only access.
    runs_map: dict = getattr(store, "_runs", {})
    if not runs_map:
        return []
    seen: dict[str, dict] = {}
    for check_id, run_list in runs_map.items():
        if run_list:
            cid = str(check_id)
            latest = max(run_list, key=lambda r: getattr(r, "finished_at", 0))
            seen[cid] = _run_to_dict(latest)
    return sorted(seen.values(), key=lambda r: r["check_id"])


def _get_runs_for_check(store: "ResultsStore", check_id: str) -> list[dict]:
    """Return up to 50 runs for the given check_id string."""
    try:
        uid = UUID(check_id)
    except ValueError:
        return []
    try:
        runs = store.list_runs(uid, limit=50)
        return [_run_to_dict(r) for r in runs]
    except Exception:
        return []


def _run_to_dict(run) -> dict:
    verdict = getattr(run, "verdict", "pass")
    # Verdict is a str-Enum; use .value so templates get the plain string ("pass"/"warn"/"fail")
    verdict_str = verdict.value if hasattr(verdict, "value") else str(verdict)
    return {
        "check_id": str(getattr(run, "check_id", "unknown")),
        "score": float(getattr(run, "score", 0.0)),
        "verdict": verdict_str,
        "plain_english": getattr(run, "plain_english", ""),
        "ran_at": str(getattr(run, "finished_at", getattr(run, "ran_at", ""))),
    }


def _get_profile_reports(store: "ResultsStore") -> list[dict]:
    list_fn = getattr(store, "list_profile_reports", None)
    if list_fn is None:
        return []
    reports = list_fn()
    return [
        {
            "report_id": str(r.report_id),
            "dataset_name": r.dataset_name,
            "ran_at": str(r.ran_at),
            "n_rows": r.n_rows,
            "n_numeric_columns": r.n_numeric_columns,
            "n_columns": len(r.columns),
        }
        for r in sorted(reports, key=lambda r: r.dataset_name)
    ]


def _get_profile_report_by_name(store: "ResultsStore", dataset_name: str) -> dict | None:
    list_fn = getattr(store, "list_profile_reports", None)
    if list_fn is None:
        return None
    # Return the most recent report for the given dataset name
    matches = [r for r in list_fn() if r.dataset_name == dataset_name]
    if not matches:
        return None
    report = sorted(matches, key=lambda r: r.ran_at)[-1]
    return {
        "report_id": str(report.report_id),
        "dataset_name": report.dataset_name,
        "ran_at": str(report.ran_at),
        "n_rows": report.n_rows,
        "n_numeric_columns": report.n_numeric_columns,
        "columns": report.columns,
    }


def _get_causality_reports(store: "ResultsStore") -> list[dict]:
    list_fn = getattr(store, "list_causality_reports", None)
    if list_fn is None:
        return []
    reports = list_fn()
    # Show edges from all reports, annotated with dataset name
    all_edges: list[dict] = []
    for r in sorted(reports, key=lambda r: r.ran_at):
        for edge in r.edges:
            all_edges.append({**edge, "dataset_name": r.dataset_name, "ran_at": str(r.ran_at)})
    # Deduplicate by (dataset, cause, effect) keeping last
    seen: dict[tuple, dict] = {}
    for e in all_edges:
        seen[(e["dataset_name"], e["cause"], e["effect"])] = e
    return sorted(seen.values(), key=lambda e: (e["dataset_name"], -_strength_order(e.get("evidence_strength", "none"))))


def _strength_order(strength: str) -> int:
    return {"strong": 3, "moderate": 2, "weak": 1, "none": 0}.get(strength, 0)


def _get_all_incidents(store: "ResultsStore") -> list[dict]:
    """Return all incidents across all check_ids, newest first.

    Accesses MemoryStore._incidents directly (read-only); non-MemoryStore
    backends with no public list-all API return empty until one is added.
    """
    incidents_map: dict = getattr(store, "_incidents", {})
    result = []
    for check_id, inc_list in incidents_map.items():
        for inc in inc_list:
            sev = getattr(inc, "severity", "fail")
            result.append({
                "check_id": str(check_id),
                "incident_id": str(getattr(inc, "incident_id", "")),
                "severity": sev.value if hasattr(sev, "value") else str(sev),
                "score": float(getattr(inc, "score", 0.0)),
                "opened_at": str(getattr(inc, "opened_at", "")),
                "status": getattr(inc, "status", "open"),
                "detector_slug": getattr(inc, "detector_slug", ""),
            })
    return sorted(result, key=lambda r: r["opened_at"], reverse=True)


def _get_incident_detail(store: "ResultsStore", check_id: str) -> dict:
    """Return runs and incidents for a single check_id string."""
    try:
        uid = UUID(check_id)
    except ValueError:
        return {"runs": [], "incidents": []}
    runs: list[dict] = []
    incidents: list[dict] = []
    try:
        runs = [_run_to_dict(r) for r in store.list_runs(uid, limit=50)]
    except Exception:
        pass
    try:
        raw_incidents = store.list_incidents(uid)
        for inc in raw_incidents:
            sev = getattr(inc, "severity", "fail")
            incidents.append({
                "incident_id": str(getattr(inc, "incident_id", "")),
                "detector_slug": getattr(inc, "detector_slug", ""),
                "severity": sev.value if hasattr(sev, "value") else str(sev),
                "score": float(getattr(inc, "score", 0.0)),
                "opened_at": str(getattr(inc, "opened_at", "")),
                "status": getattr(inc, "status", "open"),
            })
    except Exception:
        pass
    return {"runs": runs, "incidents": incidents}
