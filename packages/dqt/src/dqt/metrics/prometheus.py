# packages/dqt/src/dqt/metrics/prometheus.py
"""Prometheus text-format metrics builder for dqt. No runtime deps required."""
from __future__ import annotations
from typing import TYPE_CHECKING
from dqt.algorithms._base import Verdict

if TYPE_CHECKING:
    from dqt.store._protocol import ResultsStore


def _verdict_to_int(v: Verdict) -> int:
    return {Verdict.pass_: 0, Verdict.warn: 1, Verdict.fail: 2}[v]


def build_metrics_text(store: "ResultsStore") -> str:
    """Build Prometheus text-format metrics from the store's latest run per check.

    Metrics:
      dqt_check_score{check_id, detector_slug} -- latest score [0,1]
      dqt_check_verdict{check_id, detector_slug} -- 0=pass, 1=warn, 2=fail
      dqt_check_runs_total{check_id, detector_slug} -- total run count
    """
    lines = [
        "# HELP dqt_check_score Latest score from the most recent check run",
        "# TYPE dqt_check_score gauge",
        "# HELP dqt_check_verdict Latest verdict: 0=pass, 1=warn, 2=fail",
        "# TYPE dqt_check_verdict gauge",
        "# HELP dqt_check_runs_total Total number of runs for this check",
        "# TYPE dqt_check_runs_total gauge",
    ]

    all_incidents = store.list_all_incidents()
    seen: set[str] = set()

    for incident in all_incidents:
        cid = str(incident.check_id)
        if cid in seen:
            continue
        runs = store.list_runs(incident.check_id, limit=1)
        if not runs:
            continue
        latest = runs[0]
        seen.add(cid)
        slug = latest.detector_slug
        v = _verdict_to_int(latest.verdict)
        all_runs = store.list_runs(incident.check_id, limit=10_000)
        lines.append(f'dqt_check_score{{check_id="{cid}",detector_slug="{slug}"}} {latest.score}')
        lines.append(f'dqt_check_verdict{{check_id="{cid}",detector_slug="{slug}"}} {v}')
        lines.append(f'dqt_check_runs_total{{check_id="{cid}",detector_slug="{slug}"}} {len(all_runs)}')

    return "\n".join(lines) + "\n"


def make_wsgi_app(store: "ResultsStore"):
    """Return a WSGI app that serves /metrics."""
    def _app(environ, start_response):
        if environ.get("PATH_INFO") == "/metrics":
            try:
                text = build_metrics_text(store)
                status = "200 OK"
                headers = [("Content-Type", "text/plain; version=0.0.4; charset=utf-8")]
            except Exception as exc:
                text = f"# ERROR: {exc}\n"
                status = "500 Internal Server Error"
                headers = [("Content-Type", "text/plain")]
            start_response(status, headers)
            return [text.encode("utf-8")]
        start_response("404 Not Found", [("Content-Type", "text/plain")])
        return [b"Not found\n"]
    return _app
