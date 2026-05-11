from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

import pandas as pd

from dqt.algorithms._base import Verdict
from dqt.utils.logging import get_logger

if TYPE_CHECKING:
    from dqt.adapters._protocol import WarehouseAdapter
    from dqt.algorithms._base import DetectorState
    from dqt.checks.models import Check
    from dqt.store._protocol import ResultsStore, RunResult

_log = get_logger(__name__)


class Runner:
    """
    Orchestrates detector fit + score against a WarehouseAdapter.
    States are cached in-memory; call fit() explicitly to re-baseline,
    or let run() auto-fit on first execution.
    """

    def __init__(self, store: ResultsStore) -> None:
        self._store = store
        self._states: dict[UUID, DetectorState] = {}

    def fit(self, check: Check, adapter: WarehouseAdapter) -> None:
        from dqt.algorithms._registry import registry
        cls = registry.get(check.detector_slug)
        detector = cls(**(check.params or {}))
        ref_df = self._fetch(check, adapter)
        self._states[check.id] = detector.fit(ref_df)
        _log.info("fit", check_id=str(check.id), slug=check.detector_slug)

    def run(self, check: Check, adapter: WarehouseAdapter) -> RunResult:
        from dqt.algorithms._registry import registry
        from dqt.store._protocol import Incident, RunResult

        if check.id not in self._states:
            self.fit(check, adapter)

        cls = registry.get(check.detector_slug)
        detector = cls(**(check.params or {}))
        state = self._states[check.id]

        started_at = datetime.now(timezone.utc)
        # Pass the same detector instance to _fetch so aggregate detectors can store
        # the column name during get_aggregations() and use it in score().
        curr_df = self._fetch(check, adapter, detector=detector)
        result = detector.score(curr_df, state)
        if check.warn_threshold is not None or check.fail_threshold is not None:
            from dqt.algorithms._base import compute_verdict
            result.verdict = compute_verdict(
                result.score, check.detector_slug,
                check.warn_threshold, check.fail_threshold,
            )
        finished_at = datetime.now(timezone.utc)

        diagnostic_sql: str | None = None
        if result.failing_filter_sql and result.verdict != Verdict.pass_:
            fq_table = f"{check.schema_name}.{check.table_name}"
            diagnostic_sql = (
                f"SELECT * FROM {fq_table}\n"
                f"WHERE {result.failing_filter_sql}\n"
                f"LIMIT 20;"
            )

        run_result = RunResult(
            check_id=check.id,
            detector_slug=check.detector_slug,
            started_at=started_at,
            finished_at=finished_at,
            verdict=result.verdict,
            score=result.score,
            plain_english=result.plain_english,
            details=result.details,
            diagnostic_sql=diagnostic_sql,
        )
        self._store.save_run(run_result)

        if result.verdict != Verdict.pass_:
            self._store.save_incident(Incident(
                check_id=check.id,
                run_id=run_result.run_id,
                detector_slug=check.detector_slug,
                severity=result.verdict,
                opened_at=finished_at,
                score=result.score,
            ))

        _log.info(
            "run",
            check_id=str(check.id),
            slug=check.detector_slug,
            verdict=result.verdict.value,
            score=result.score,
        )
        return run_result

    def _fetch(
        self,
        check: "Check",
        adapter: "WarehouseAdapter",
        detector: "DetectorState | None" = None,
    ) -> pd.DataFrame:
        """Fetch data for a check, applying scope, filters, and sampling settings."""
        from dqt.algorithms._registry import registry
        if detector is None:
            cls = registry.get(check.detector_slug)
            detector = cls(**(check.params or {}))

        if detector.kind == "aggregate":
            col = check.column_name or "*"
            exprs = detector.get_aggregations(col)
            agg_result = adapter.aggregate(check.schema_name, check.table_name, exprs)
            return pd.DataFrame([agg_result])

        # Build kwargs for sample()
        kwargs: dict = {}

        # Scope: pass incremental/custom scope details to adapter
        if check.scope is not None:
            kwargs["scope"] = check.scope
            if check.scope.key_col:
                kwargs["key_col"] = check.scope.key_col
            if check.scope.since:
                kwargs["since"] = check.scope.since

        # Filters: pass column filters to adapter
        if check.filters:
            kwargs["filters"] = check.filters

        # sampling_pct takes priority over sample_n when set
        if check.sampling_pct is not None:
            df = adapter.sample(
                check.schema_name, check.table_name, check.sample_n,
                sampling_pct=check.sampling_pct, **kwargs
            )
        else:
            df = adapter.sample(check.schema_name, check.table_name, check.sample_n, **kwargs)

        # Project to the target column so every sample-kind detector reliably receives
        # a single-column DataFrame regardless of table width.  Without this, detectors
        # using iloc[:, 0] silently score whichever column happens to be first.
        if check.column_name and check.column_name in df.columns:
            return df[[check.column_name]]
        return df
