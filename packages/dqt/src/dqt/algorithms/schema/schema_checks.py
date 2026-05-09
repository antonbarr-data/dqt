# packages/dqt/src/dqt/algorithms/schema/schema_checks.py
# Detects column additions, removals, and type changes between schema snapshots.
from __future__ import annotations

import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry


@registry.register
class SchemaChangeDetector(BaseDetector):
    """
    fit() expects a DataFrame with columns [col_name, data_type] from describe_columns().
    score() compares current schema to baseline and returns 1.0 on any change, 0.0 otherwise.
    """
    slug = "schema_change"
    group = "schema"

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return dict(zip(reference["col_name"], reference["data_type"]))

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr_schema = dict(zip(current["col_name"], current["data_type"]))
        baseline_schema: dict[str, str] = state

        added = set(curr_schema) - set(baseline_schema)
        removed = set(baseline_schema) - set(curr_schema)
        type_changed = {
            col for col in (set(curr_schema) & set(baseline_schema))
            if curr_schema[col] != baseline_schema[col]
        }

        if not added and not removed and not type_changed:
            return DetectorResult(
                score=0.0,
                verdict=Verdict.pass_,
                plain_english="Schema unchanged.",
                details={},
            )

        parts: list[str] = []
        if added:
            parts.append(f"added: {sorted(added)}")
        if removed:
            parts.append(f"removed: {sorted(removed)}")
        if type_changed:
            parts.append(f"type changed: {sorted(type_changed)}")
        msg = "; ".join(parts)

        return DetectorResult(
            score=1.0,
            verdict=Verdict.fail,
            plain_english=f"Schema changed — {msg}",
            details={"added": sorted(added), "removed": sorted(removed), "type_changed": sorted(type_changed)},
        )
