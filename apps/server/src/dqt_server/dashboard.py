"""Minimal HTMX incident dashboard — auth-free, MemoryStore-backed.

No external deps beyond stdlib + fastapi. No Jinja2, no template files.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from dqt.algorithms._base import DetectorResult, Verdict

router = APIRouter(tags=["dashboard"])

# ---------------------------------------------------------------------------
# In-process state
# ---------------------------------------------------------------------------

@dataclass
class _RunRecord:
    check_id: str
    detector_slug: str
    result: DetectorResult
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DashboardState:
    """Singleton holding all run history for the dashboard."""

    def __init__(self) -> None:
        self._runs: dict[str, list[_RunRecord]] = {}

    def add_result(self, check_id: str, result: DetectorResult, detector_slug: str) -> None:
        self._runs.setdefault(check_id, []).append(
            _RunRecord(check_id=check_id, detector_slug=detector_slug, result=result)
        )

    def get_history(self, check_id: str) -> list[_RunRecord]:
        return self._runs.get(check_id, [])[-20:]

    def all_latest(self) -> list[_RunRecord]:
        """One record per check_id — the most recent run."""
        return [runs[-1] for runs in self._runs.values() if runs]

    def check_ids(self) -> list[str]:
        return list(self._runs.keys())


STATE = DashboardState()

# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

_BADGE = {
    Verdict.pass_: ("pass", "#4ade80"),
    Verdict.warn:  ("warn", "#facc15"),
    Verdict.fail:  ("fail", "#f87171"),
}

_HTMX_CDN = "https://unpkg.com/htmx.org@1.9.12"
_TAILWIND_CDN = "https://cdn.tailwindcss.com"


def _base(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en" class="bg-gray-950 text-gray-100">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{title}</title>
  <script src="{_TAILWIND_CDN}"></script>
  <script src="{_HTMX_CDN}"></script>
  <style>
    body {{ font-family: 'JetBrains Mono', monospace; }}
    .badge-pass {{ background:#14532d; color:#4ade80; }}
    .badge-warn {{ background:#713f12; color:#facc15; }}
    .badge-fail {{ background:#7f1d1d; color:#f87171; }}
  </style>
</head>
<body class="min-h-screen">
  <header class="border-b border-gray-800 px-6 py-3 flex items-center gap-4">
    <span class="text-sm font-light tracking-widest text-gray-400">dqt dashboard</span>
    <a href="/dashboard" class="ml-auto text-xs text-gray-500 hover:text-gray-300">all checks</a>
  </header>
  <main class="px-6 py-6 max-w-5xl mx-auto">
    {body}
  </main>
</body>
</html>"""


def _verdict_badge(verdict: Verdict) -> str:
    label, _ = _BADGE[verdict]
    return f'<span class="badge-{label} text-xs px-2 py-0.5 font-mono">{label}</span>'


def _sparkline(records: list[_RunRecord]) -> str:
    """Inline SVG sparkline of scores (last ≤20 points)."""
    if not records:
        return ""
    scores = [r.result.score for r in records]
    mn, mx = min(scores), max(scores)
    span = mx - mn if mx != mn else 1.0
    W, H = 200, 36
    pts = []
    for i, s in enumerate(scores):
        x = int(i / max(len(scores) - 1, 1) * W)
        y = int(H - (s - mn) / span * (H - 4) - 2)
        pts.append(f"{x},{y}")
    polyline = " ".join(pts)
    return (
        f'<svg width="{W}" height="{H}" class="overflow-visible">'
        f'<polyline points="{polyline}" fill="none" stroke="#9DD0B0" stroke-width="1.5"/>'
        f"</svg>"
    )


def _details_table(details: dict[str, Any]) -> str:
    if not details:
        return "<p class='text-gray-500 text-xs'>No details.</p>"
    rows = ""
    for k, v in details.items():
        v_str = json.dumps(v) if not isinstance(v, str) else v
        rows += (
            f"<tr class='border-b border-gray-800'>"
            f"<td class='py-1 pr-4 text-gray-400 text-xs whitespace-nowrap'>{k}</td>"
            f"<td class='py-1 font-mono text-xs text-gray-200 break-all'>{v_str}</td>"
            f"</tr>"
        )
    return f"<table class='w-full text-left'><tbody>{rows}</tbody></table>"


# ---------------------------------------------------------------------------
# Result fragment (shared by detail page and HTMX re-run response)
# ---------------------------------------------------------------------------

def _result_fragment(check_id: str) -> str:
    history = STATE.get_history(check_id)
    if not history:
        return "<p class='text-gray-500'>No runs recorded for this check.</p>"

    latest = history[-1]
    r = latest.result
    label, color = _BADGE[r.verdict]

    spark = _sparkline(history)
    details_html = _details_table(r.details)
    score_fmt = f"{r.score:.4f}"

    return f"""
<div id="result-fragment">
  <div class="flex items-center gap-4 mb-4">
    {_verdict_badge(r.verdict)}
    <span class="font-mono text-2xl font-light" style="color:{color}">{score_fmt}</span>
    <span class="text-xs text-gray-500">{latest.ts.strftime('%Y-%m-%d %H:%M:%S UTC')}</span>
  </div>

  <div class="mb-4">
    <p class="text-sm text-gray-300">{r.plain_english}</p>
  </div>

  <div class="mb-6">
    <p class="text-xs text-gray-500 mb-1">score history (last {len(history)} runs)</p>
    {spark}
  </div>

  <div class="mb-4">
    <p class="text-xs text-gray-500 mb-1">details</p>
    {details_html}
  </div>

  {"<div class='mb-4'><p class='text-xs text-gray-500 mb-1'>failing filter SQL</p>"
    + f"<code class='block bg-gray-900 border border-gray-700 px-3 py-2 text-xs text-amber-300 overflow-x-auto whitespace-pre'>{r.failing_filter_sql}</code></div>"
    if r.failing_filter_sql else ""}
</div>
"""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_index() -> HTMLResponse:
    rows = ""
    for rec in STATE.all_latest():
        r = rec.result
        rows += (
            f"<tr class='border-b border-gray-800 hover:bg-gray-900 cursor-pointer'"
            f" onclick=\"location.href='/dashboard/checks/{rec.check_id}'\">"
            f"<td class='py-2 pr-4 font-mono text-xs text-gray-300'>{rec.check_id}</td>"
            f"<td class='py-2 pr-4 text-xs text-gray-400'>{rec.detector_slug}</td>"
            f"<td class='py-2 pr-4'>{_verdict_badge(r.verdict)}</td>"
            f"<td class='py-2 pr-4 font-mono text-xs text-gray-200'>{r.score:.4f}</td>"
            f"<td class='py-2 text-xs text-gray-500'>{rec.ts.strftime('%Y-%m-%d %H:%M')}</td>"
            f"</tr>"
        )

    if not rows:
        rows = (
            "<tr><td colspan='5' class='py-6 text-center text-gray-600 text-sm'>"
            "No check runs yet. Use <code>dashboard.STATE.add_result(...)</code> to populate."
            "</td></tr>"
        )

    body = f"""
<h1 class="text-sm font-light tracking-widest text-gray-400 mb-4">checks</h1>
<table class="w-full text-left">
  <thead>
    <tr class="border-b border-gray-700">
      <th class="pb-2 text-xs text-gray-500 font-normal pr-4">check id</th>
      <th class="pb-2 text-xs text-gray-500 font-normal pr-4">detector</th>
      <th class="pb-2 text-xs text-gray-500 font-normal pr-4">verdict</th>
      <th class="pb-2 text-xs text-gray-500 font-normal pr-4">score</th>
      <th class="pb-2 text-xs text-gray-500 font-normal">last run</th>
    </tr>
  </thead>
  <tbody>
    {rows}
  </tbody>
</table>
"""
    return HTMLResponse(_base("dqt dashboard", body))


@router.get("/dashboard/checks/{check_id}", response_class=HTMLResponse)
def dashboard_check_detail(check_id: str) -> HTMLResponse:
    body = f"""
<div class="flex items-center gap-3 mb-6">
  <a href="/dashboard" class="text-xs text-gray-600 hover:text-gray-400">&larr; all checks</a>
  <h1 class="text-xs font-mono text-gray-400">{check_id}</h1>
  <button
    class="ml-auto text-xs bg-gray-800 hover:bg-gray-700 border border-gray-700 px-3 py-1"
    hx-post="/dashboard/checks/{check_id}/run"
    hx-target="#result-fragment"
    hx-swap="outerHTML"
  >re-run</button>
</div>
{_result_fragment(check_id)}
"""
    return HTMLResponse(_base(f"dqt — {check_id}", body))


@router.post("/dashboard/checks/{check_id}/run", response_class=HTMLResponse)
def dashboard_check_run(check_id: str) -> HTMLResponse:
    """HTMX partial: re-executes the last known result (no live adapter connected).

    In a real deployment this would call the Runner; here we replay the last
    stored result so the fragment swaps correctly without a warehouse connection.
    """
    history = STATE.get_history(check_id)
    if history:
        last = history[-1]
        STATE.add_result(check_id, last.result, last.detector_slug)
    return HTMLResponse(_result_fragment(check_id))
