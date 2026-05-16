"""Channel A: data integrity scanner.

Scans failed/warned check runs within the analysis window and estimates their
fractional contribution to the observed metric movement using a conservative
heuristic: fail -> 10-30%, warn -> 3-10%. Sorted by upper-bound contribution.
"""
from __future__ import annotations

from datetime import datetime

from dqt.store._protocol import ResultsStore
from dqt.insights.models import DataIssue, EvidenceRow


_CONTRIBUTION = {
    "fail": (0.10, 0.30),
    "warn": (0.03, 0.10),
}


def scan(
    metric_fqn: str,
    window_start: datetime,
    window_end: datetime,
    store: ResultsStore,
) -> list[DataIssue]:
    """Return DataIssues for non-passing check runs in the window.

    NOTE: RunResult has no metric_fqn field, so results are currently global across all
    metrics. Filtering will be added once check runs carry a metric FK in the store.
    """
    runs = store.query_runs(since=window_start, until=window_end, limit=500)
    issues: list[DataIssue] = []
    for run in runs:
        verdict_str = run.verdict.value if hasattr(run.verdict, "value") else str(run.verdict)
        if verdict_str not in _CONTRIBUTION:
            continue
        low, high = _CONTRIBUTION[verdict_str]
        evidence = EvidenceRow(
            source=f"check:{run.detector_slug}",
            signal_type="failed_check",
            magnitude=(low + high) / 2,
            magnitude_low=low,
            magnitude_high=high,
            evidence_strength="strong" if verdict_str == "fail" else "moderate",
            detail={
                "score": run.score,
                "plain_english": run.plain_english,
                "check_id": str(run.check_id),
            },
        )
        issues.append(DataIssue(
            check_id=run.check_id,
            detector_slug=run.detector_slug,
            verdict=verdict_str,
            run_at=run.started_at,
            contribution_low=low,
            contribution_high=high,
            evidence=evidence,
        ))
    return sorted(issues, key=lambda i: i.contribution_high, reverse=True)
