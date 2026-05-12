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
            request, "index.html", {"runs": runs, "title": "dqt"}
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
            seen[cid] = _run_to_dict(run_list[-1])
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
