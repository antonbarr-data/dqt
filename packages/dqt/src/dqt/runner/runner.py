from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pandas as pd

from dqt.algorithms._base import Verdict
from dqt.utils.logging import get_logger

if TYPE_CHECKING:
    from dqt.adapters._protocol import WarehouseAdapter
    from dqt.algorithms._base import CostEstimate, DetectorState
    from dqt.checks.models import Check
    from dqt.store._protocol import ResultsStore, RunResult

_VersionedState = tuple[str, "DetectorState"]  # (detector_version, state)


@dataclass
class SuiteResult:
    """Result of Runner.run_suite() across multiple checks."""
    ran: list[RunResult] = field(default_factory=list)
    skipped: list[tuple[Check, str]] = field(default_factory=list)  # (check, reason)
    budget_spent_usd: float = 0.0
    budget_total_usd: float = 0.0

_log = get_logger(__name__)


class Runner:
    """
    Orchestrates detector fit + score against a WarehouseAdapter.
    States are cached in-memory; call fit() explicitly to re-baseline,
    or let run() auto-fit on first execution.
    """

    def __init__(
        self,
        store: ResultsStore,
        emitter=None,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
    ) -> None:
        self._store = store
        self._states: dict[UUID, _VersionedState] = {}
        self._emitter = emitter
        self._max_retries = max_retries
        self._retry_delay = retry_delay_seconds

    def fit(self, check: Check, adapter: WarehouseAdapter) -> None:
        from dqt.algorithms._registry import registry
        cls = registry.get(check.detector_slug)
        detector = cls(**(check.params or {}))
        ref_df = self._fetch(check, adapter)
        self._states[check.id] = (cls.version, detector.fit(ref_df))
        _log.info("fit", check_id=str(check.id), slug=check.detector_slug)

    def run(self, check: Check, adapter: WarehouseAdapter) -> RunResult:
        import time
        from dqt.lineage.openlineage import RunState
        from dqt.store._protocol import Incident, RunResult

        _RETRYABLE = (TimeoutError, OSError, ConnectionError)

        job_name = f"{check.schema_name}.{check.table_name}.{check.detector_slug}"
        run_id = str(check.id)

        if self._emitter is not None:
            try:
                self._emitter.emit(RunState.START, job_name, run_id)
            except Exception:
                _log.warning("openlineage_emit_failed", phase="start")

        last_exc: BaseException | None = None
        result = None
        for attempt in range(self._max_retries):
            try:
                result = self._run_core(check, adapter)
                break
            except _RETRYABLE as exc:
                last_exc = exc
                _log.warning(
                    "run_retryable_error",
                    check_id=str(check.id),
                    attempt=attempt + 1,
                    max_retries=self._max_retries,
                    error=str(exc),
                )
                if attempt < self._max_retries - 1:
                    time.sleep(self._retry_delay * (2 ** attempt))
            except Exception as _exc:
                if self._emitter is not None:
                    try:
                        self._emitter.emit(RunState.FAIL, job_name, run_id, error_message=str(_exc))
                    except Exception:
                        pass
                raise

        if result is None:
            # All retries exhausted — graceful degradation
            now = datetime.now(timezone.utc)
            result = RunResult(
                run_id=uuid4(),
                check_id=check.id,
                detector_slug=check.detector_slug,
                detector_version="unknown",
                started_at=now,
                finished_at=now,
                verdict=Verdict.warn,
                score=0.0,
                plain_english=f"adapter timeout after {self._max_retries} retries: {last_exc}",
                details={"error": str(last_exc)},
            )
            self._store.save_run(result)
            self._store.save_incident(Incident(
                check_id=check.id,
                run_id=result.run_id,
                detector_slug=check.detector_slug,
                severity=Verdict.warn,
                opened_at=now,
                score=0.0,
            ))
            if self._emitter is not None:
                try:
                    self._emitter.emit(RunState.FAIL, job_name, run_id, error_message=str(last_exc))
                except Exception:
                    pass
            return result

        if self._emitter is not None:
            try:
                self._emitter.emit(RunState.COMPLETE, job_name, run_id)
            except Exception:
                _log.warning("openlineage_emit_failed", phase="complete")

        return result

    def _run_core(self, check: Check, adapter: WarehouseAdapter) -> RunResult:
        from dqt.algorithms._registry import registry
        from dqt.store._protocol import Incident, RunResult

        if check.id not in self._states:
            self.fit(check, adapter)

        cls = registry.get(check.detector_slug)
        detector = cls(**(check.params or {}))
        cached_version, state = self._states[check.id]
        if cached_version != cls.version:
            _log.warning(
                "detector_version_changed_refitting",
                check_id=str(check.id),
                slug=check.detector_slug,
                cached_version=cached_version,
                current_version=cls.version,
            )
            self.fit(check, adapter)
            _, state = self._states[check.id]

        started_at = datetime.now(timezone.utc)
        # Pass the same detector instance to _fetch so aggregate detectors can store
        # the column name during get_aggregations() and use it in score().
        curr_df = self._fetch(check, adapter, detector=detector)
        n_rows = len(curr_df)
        _power_prefix = (
            f"[low-power: N={n_rows} < recommended {detector.min_recommended_n}] "
            if n_rows < detector.min_recommended_n
            else ""
        )

        # Degenerate-distribution guard: >90% null or <5 unique non-null values
        # means sparsity is the quality signal — outlier detectors would produce
        # meaningless results on such data.
        if check.column_name and detector.kind == "sample":
            _col_data = curr_df.iloc[:, 0] if not curr_df.empty else pd.Series([], dtype=float)
            _non_null_frac = float(_col_data.notna().mean()) if len(_col_data) > 0 else 0.0
            _n_unique = int(_col_data.nunique(dropna=True))
            if _non_null_frac < 0.1 or _n_unique < 5:
                finished_at = datetime.now(timezone.utc)
                run_result = RunResult(
                    check_id=check.id,
                    detector_slug=check.detector_slug,
                    started_at=started_at,
                    finished_at=finished_at,
                    verdict=Verdict.warn,
                    score=0.0,
                    plain_english=(
                        f"degenerate_distribution_detected: "
                        f"{_non_null_frac:.0%} non-null, {_n_unique} unique values — "
                        "sparsity is the quality signal; outlier detection skipped"
                    ),
                    details={
                        "degenerate": True,
                        "non_null_fraction": _non_null_frac,
                        "n_unique": _n_unique,
                    },
                    detector_version=cls.version,
                )
                self._store.save_run(run_result)
                self._store.save_incident(Incident(
                    check_id=check.id,
                    run_id=run_result.run_id,
                    detector_slug=check.detector_slug,
                    severity=Verdict.warn,
                    opened_at=finished_at,
                    score=0.0,
                ))
                _log.info(
                    "run_degenerate",
                    check_id=str(check.id),
                    slug=check.detector_slug,
                    non_null_frac=_non_null_frac,
                    n_unique=_n_unique,
                )
                return run_result

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
            plain_english=_power_prefix + result.plain_english,
            details=result.details,
            diagnostic_sql=diagnostic_sql,
            detector_version=cls.version,
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

    def dry_run(self, check: Check, adapter: WarehouseAdapter) -> tuple:
        """Return the SQL that would be executed and a CostEstimate, without running."""
        from dqt.algorithms._base import CostEstimate
        from dqt.algorithms._registry import registry

        cls = registry.get(check.detector_slug)
        detector = cls(**(check.params or {}))
        cost = detector.estimate_cost(row_count=100_000)

        col = getattr(check, "column_name", None)
        schema = getattr(check, "schema_name", "public")
        table = getattr(check, "table_name", "unknown")
        if col:
            sql = f"SELECT {col} FROM {schema}.{table} TABLESAMPLE SYSTEM (10) LIMIT 100000"
        else:
            sql = f"SELECT * FROM {schema}.{table} TABLESAMPLE SYSTEM (10) LIMIT 100000"
        return sql, cost

    def run_suite(
        self,
        checks: list[Check],
        adapter: WarehouseAdapter,
        cost_budget_usd: float = 10.0,
        parallelism: int = 1,
    ) -> SuiteResult:
        """Run multiple checks in cost order, stopping when the budget is exhausted.

        Checks are sorted cheapest-first by CostEstimate.warehouse_cost_usd so the most
        impactful low-cost checks always run. When a check would push the cumulative spend
        past cost_budget_usd it is recorded as skipped rather than dropped silently.

        Args:
            checks: list of Check definitions to run
            adapter: warehouse adapter to fetch data from
            cost_budget_usd: maximum total warehouse cost allowed across the suite
        """
        from dqt.algorithms._registry import registry

        result = SuiteResult(budget_total_usd=cost_budget_usd)

        # Estimate cost and sort cheapest-first
        table_row_counts: dict[tuple[str, str], int] = {}

        def _row_count(check: Check) -> int:
            key = (check.schema_name, check.table_name)
            if key not in table_row_counts:
                try:
                    cols = adapter.describe_columns(check.schema_name, check.table_name)
                    table_row_counts[key] = cols[0].row_count if cols and cols[0].row_count else 100_000
                except Exception:
                    table_row_counts[key] = 100_000
            return table_row_counts[key]

        def _cost(check: Check) -> CostEstimate:
            try:
                cls = registry.get(check.detector_slug)
                det = cls(**(check.params or {}))
                return det.estimate_cost(
                    row_count=_row_count(check),
                    sample_n=check.sample_n,
                )
            except Exception:
                from dqt.algorithms._base import CostEstimate
                return CostEstimate(rows_scanned=100_000, warehouse_cost_usd=0.0, wall_time_seconds=1.0)

        ranked = sorted(checks, key=lambda c: _cost(c).warehouse_cost_usd)

        to_run = []
        for check in ranked:
            est = _cost(check)
            if result.budget_spent_usd + est.warehouse_cost_usd > cost_budget_usd:
                reason = (
                    f"cost estimate ${est.warehouse_cost_usd:.4f} would exceed "
                    f"remaining budget ${cost_budget_usd - result.budget_spent_usd:.4f}"
                )
                result.skipped.append((check, reason))
                _log.info(
                    "run_suite_skipped",
                    check_id=str(check.id),
                    slug=check.detector_slug,
                    reason=reason,
                )
            else:
                to_run.append(check)
                result.budget_spent_usd += _cost(check).warehouse_cost_usd

        if parallelism <= 1:
            for check in to_run:
                result.ran.append(self.run(check, adapter))
        else:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=parallelism) as pool:
                futures = {pool.submit(self.run, check, adapter): check for check in to_run}
                for future in as_completed(futures):
                    try:
                        result.ran.append(future.result())
                    except Exception as exc:
                        _log.error(
                            "suite_check_failed",
                            check_id=str(futures[future].id),
                            error=str(exc),
                        )

        _log.info(
            "run_suite_complete",
            ran=len(result.ran),
            skipped=len(result.skipped),
            budget_spent_usd=result.budget_spent_usd,
        )
        return result
