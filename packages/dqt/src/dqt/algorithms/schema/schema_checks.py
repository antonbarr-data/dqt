# packages/dqt/src/dqt/algorithms/schema/schema_checks.py
# Detects column additions, removals, type changes, and renames between schema snapshots.
from __future__ import annotations

import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry


def _levenshtein(a: str, b: str) -> int:
    """Classic dynamic-programming Levenshtein distance."""
    if len(a) < len(b):
        return _levenshtein(b, a)
    if len(b) == 0:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr_row = [i + 1]
        for j, cb in enumerate(b):
            curr_row.append(min(prev[j + 1] + 1, curr_row[j] + 1, prev[j] + (ca != cb)))
        prev = curr_row
    return prev[-1]


def _detect_renames(
    missing: list[str],
    added: list[str],
    ref_dtypes: dict[str, str],
    curr_dtypes: dict[str, str],
    max_dist: int = 2,
) -> list[dict]:
    """Match removed columns to added columns by Levenshtein distance + same dtype."""
    renames: list[dict] = []
    used_added: set[str] = set()
    for m in missing:
        best_dist = max_dist + 1
        best_add: str | None = None
        for a in added:
            if a in used_added:
                continue
            dist = _levenshtein(m, a)
            if dist <= max_dist and dist < best_dist:
                if str(ref_dtypes.get(m, "")) == str(curr_dtypes.get(a, "")):
                    best_dist = dist
                    best_add = a
        if best_add is not None:
            renames.append({"from": m, "to": best_add, "levenshtein_dist": best_dist})
            used_added.add(best_add)
    return renames


@registry.register
class SchemaChangeDetector(BaseDetector):
    """
    fit() expects a DataFrame with columns [col_name, data_type] from describe_columns().
    score() compares current schema to baseline and returns 1.0 on any change, 0.0 otherwise.
    Renames (Levenshtein <= 2, same dtype) are surfaced in details["renamed_columns"] separately.
    """
    slug = "schema_change"
    group = "schema"

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return dict(zip(reference["col_name"], reference["data_type"]))

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr_schema = dict(zip(current["col_name"], current["data_type"]))
        baseline_schema: dict[str, str] = state

        added_set = set(curr_schema) - set(baseline_schema)
        removed_set = set(baseline_schema) - set(curr_schema)
        type_changed = {
            col for col in (set(curr_schema) & set(baseline_schema))
            if curr_schema[col] != baseline_schema[col]
        }

        # Fuzzy rename detection — must happen before finalising added/removed lists
        renames = _detect_renames(
            missing=sorted(removed_set),
            added=sorted(added_set),
            ref_dtypes={c: str(baseline_schema.get(c, "")) for c in removed_set},
            curr_dtypes={c: str(curr_schema.get(c, "")) for c in added_set},
        )
        renamed_froms = {r["from"] for r in renames}
        renamed_tos = {r["to"] for r in renames}
        added = sorted(added_set - renamed_tos)
        removed = sorted(removed_set - renamed_froms)

        if not added and not removed and not type_changed and not renames:
            return DetectorResult(
                score=0.0,
                verdict=Verdict.pass_,
                plain_english="Schema unchanged.",
                details={"renamed_columns": []},
            )

        parts: list[str] = []
        if added:
            parts.append(f"added: {added}")
        if removed:
            parts.append(f"removed: {removed}")
        if type_changed:
            parts.append(f"type changed: {sorted(type_changed)}")
        if renames:
            parts.append(f"renamed: {[(r['from'], r['to']) for r in renames]}")
        msg = "; ".join(parts)

        return DetectorResult(
            score=1.0,
            verdict=Verdict.fail,
            plain_english=f"Schema changed — {msg}",
            details={
                "added": added,
                "removed": removed,
                "type_changed": sorted(type_changed),
                "renamed_columns": renames,
            },
        )
