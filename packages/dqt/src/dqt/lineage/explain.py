# packages/dqt/src/dqt/lineage/explain.py
"""Anomaly explanation via causal layer.

On incident creation, explain_incident() traverses the lineage graph upstream,
collects score time-series from the store for all upstream checks, and runs
Granger causality to surface the most likely upstream cause.

The score time-series from RunResult objects serve as health proxies for each
monitored column — a rising score upstream before the incident is causal evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from dqt.lineage.models import LineageGraph


@dataclass
class CausalEvidence:
    """Granger-based evidence for one upstream → failing check causal link."""
    upstream_check_id: UUID
    upstream_node_id: str
    evidence_strength: str  # "strong" | "moderate" | "weak" | "none" | "insufficient_history"
    granger_adjusted_p: float | None = None
    granger_f_statistic: float | None = None
    selected_lag: int | None = None
    n_observations: int = 0


@dataclass
class IncidentExplanation:
    """Structured causal explanation for one incident."""
    incident_id: UUID
    failing_check_id: UUID
    failing_node_id: str
    # Ordered by evidence strength: strongest first
    causes: list[CausalEvidence] = field(default_factory=list)
    plain_english: str = ""
    n_upstream_checks_found: int = 0
    n_upstream_checks_tested: int = 0


def explain_incident(
    incident,
    checks: list,
    store,
    graph: LineageGraph,
    *,
    max_upstream_depth: int = 3,
    min_history_runs: int = 20,
) -> IncidentExplanation | None:
    """Explain an incident by running Granger causality on upstream check score history.

    Algorithm:
    1. Find the Check for the incident and resolve its lineage node.
    2. Walk all_upstream() up to max_upstream_depth hops.
    3. For each upstream node, find checks that monitor it.
    4. Load score history for all those checks + the failing check.
    5. Build a score panel (rows = run index, cols = check_id).
    6. Run Granger causality: does each upstream score time-series Granger-cause
       the failing check's score time-series?
    7. Return significant edges ordered by evidence strength.

    Returns None when:
    - The incident's check cannot be resolved in the lineage graph.
    - No upstream checks share any time-indexed score history.
    """
    from dqt.lineage.dedup import _node_id_for_check

    check_map = {c.id: c for c in checks}
    node_index = {n.id: n for n in graph.nodes}

    failing_check = check_map.get(incident.check_id)
    if failing_check is None:
        return None

    failing_nid = _node_id_for_check(
        failing_check.schema_name,
        failing_check.table_name,
        failing_check.column_name,
    )
    if failing_nid not in node_index:
        return None

    # Build a node_id → check map for quick lookup
    node_to_check: dict[str, list] = {}
    for chk in checks:
        nid = _node_id_for_check(chk.schema_name, chk.table_name, chk.column_name)
        node_to_check.setdefault(nid, []).append(chk)

    # Collect upstream nodes (BFS, bounded by max_upstream_depth)
    from collections import deque
    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(failing_nid, 0)])
    upstream_nodes: list[str] = []
    while queue:
        current, depth = queue.popleft()
        if depth >= max_upstream_depth:
            continue
        for edge in graph.edges:
            if edge.target == current and edge.source not in visited and edge.source != failing_nid:
                visited.add(edge.source)
                upstream_nodes.append(edge.source)
                queue.append((edge.source, depth + 1))

    upstream_checks: list = []
    for nid in upstream_nodes:
        upstream_checks.extend(node_to_check.get(nid, []))

    explanation = IncidentExplanation(
        incident_id=incident.incident_id if hasattr(incident, "incident_id") else incident.check_id,
        failing_check_id=incident.check_id,
        failing_node_id=failing_nid,
        n_upstream_checks_found=len(upstream_checks),
    )

    if not upstream_checks:
        explanation.plain_english = "No upstream checks found in lineage graph."
        return explanation

    # Load score history for failing check and all upstream checks
    failing_scores = [r.score for r in store.list_runs(incident.check_id, limit=500)]
    upstream_score_series: dict[UUID, list[float]] = {}
    for chk in upstream_checks:
        scores = [r.score for r in store.list_runs(chk.id, limit=500)]
        if scores:
            upstream_score_series[chk.id] = scores

    if not upstream_score_series:
        explanation.plain_english = "Upstream checks have no stored run history."
        return explanation

    # Build a time-aligned panel — trim all to the minimum available length
    min_len = min(len(failing_scores), min(len(s) for s in upstream_score_series.values()))

    if min_len < min_history_runs:
        # Not enough history — return evidence with "insufficient_history" strength
        for chk in upstream_checks:
            if chk.id in upstream_score_series:
                nid = _node_id_for_check(chk.schema_name, chk.table_name, chk.column_name)
                explanation.causes.append(CausalEvidence(
                    upstream_check_id=chk.id,
                    upstream_node_id=nid,
                    evidence_strength="insufficient_history",
                    n_observations=min_len,
                ))
        explanation.plain_english = (
            f"Only {min_len} overlapping run history points available "
            f"(need {min_history_runs}). Cannot run Granger causality."
        )
        return explanation

    import numpy as np
    import pandas as pd
    from dqt.causality.granger import granger_pairwise

    failing_col = str(incident.check_id)
    panel_data: dict[str, list[float]] = {failing_col: failing_scores[:min_len]}
    check_id_to_nid: dict[str, str] = {}
    check_id_to_uuid: dict[str, UUID] = {}

    for chk in upstream_checks:
        if chk.id not in upstream_score_series:
            continue
        col_name = str(chk.id)
        panel_data[col_name] = upstream_score_series[chk.id][:min_len]
        nid = _node_id_for_check(chk.schema_name, chk.table_name, chk.column_name)
        check_id_to_nid[col_name] = nid
        check_id_to_uuid[col_name] = chk.id

    panel_df = pd.DataFrame(panel_data)
    # scores stored newest-first (list_runs returns newest first); reverse for time order
    panel_df = panel_df.iloc[::-1].reset_index(drop=True)

    tested: list[CausalEvidence] = []
    try:
        report = granger_pairwise(panel_df, max_lag=4, columns=list(panel_data.keys()))
        explanation.n_upstream_checks_tested = len(check_id_to_uuid)

        for edge in report.edges:
            if edge.effect != failing_col:
                continue
            cause_col = edge.cause
            if cause_col not in check_id_to_uuid:
                continue
            tested.append(CausalEvidence(
                upstream_check_id=check_id_to_uuid[cause_col],
                upstream_node_id=check_id_to_nid[cause_col],
                evidence_strength=edge.evidence_strength,
                granger_adjusted_p=edge.adjusted_p_value,
                granger_f_statistic=edge.f_statistic,
                selected_lag=edge.selected_lag,
                n_observations=min_len,
            ))
    except Exception:
        # Granger test failed (e.g. non-stationary after differencing) — return no_data
        pass

    # Sort by evidence strength
    _strength_order = {"strong": 0, "moderate": 1, "weak": 2, "none": 3}
    tested.sort(key=lambda e: _strength_order.get(e.evidence_strength, 99))
    explanation.causes = tested

    strong = [e for e in tested if e.evidence_strength in ("strong", "moderate")]
    if strong:
        top = strong[0]
        explanation.plain_english = (
            f"Granger causality ({top.evidence_strength} evidence, "
            f"lag={top.selected_lag}, adjusted p={top.granger_adjusted_p:.4f}): "
            f"upstream node '{top.upstream_node_id}' likely caused this failure."
        )
    elif tested:
        explanation.plain_english = (
            f"Weak or no Granger evidence across {len(tested)} upstream check(s). "
            "The failure may be local or caused by a node not in the lineage graph."
        )
    else:
        explanation.plain_english = "No Granger causality edges computed."

    return explanation
