# packages/dqt-airflow/src/dqt_airflow/operators.py
"""Airflow operators for dqt.

DqtCheckOperator   — run a single Check; fail the task on Verdict.fail
DqtSuiteOperator   — run a suite of Checks; fail the task if any verdict is fail

Both operators accept a factory callable for the Runner, adapter, and checks
so that heavyweight objects can be constructed lazily per task execution.

Usage:
    from dqt_airflow import DqtCheckOperator, DqtSuiteOperator

    run_quality = DqtSuiteOperator(
        task_id="run_dqt",
        checks_factory=lambda: load_checks(),
        runner_factory=lambda: build_runner(),
        adapter_factory=lambda: build_adapter(),
    )
"""
from __future__ import annotations

from typing import Any, Callable


class _BaseOperator:
    """Minimal Airflow BaseOperator shim that works with and without airflow installed."""
    ui_color = "#00a000"

    def __init__(self, task_id: str, **kwargs: Any) -> None:
        try:
            from airflow.models import BaseOperator as AirflowBase
            # Let Airflow's BaseOperator handle everything
            AirflowBase.__init__(self, task_id=task_id, **kwargs)  # type: ignore[arg-type]
        except ImportError:
            self.task_id = task_id

    def execute(self, context: dict) -> Any:
        raise NotImplementedError


class DqtCheckOperator(_BaseOperator):
    """Run a single dqt Check as an Airflow task.

    Fails the task when verdict is `fail`. Warns (but does not fail) for `warn`.

    Args:
        task_id: Airflow task identifier.
        check_factory: Callable returning a `dqt.Check`.
        runner_factory: Callable returning a `dqt.Runner`.
        adapter_factory: Callable returning a `dqt.WarehouseAdapter`.
        fail_on_warn: If True, also fail the task on Verdict.warn (default False).
    """

    def __init__(
        self,
        task_id: str,
        check_factory: Callable,
        runner_factory: Callable,
        adapter_factory: Callable,
        fail_on_warn: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(task_id=task_id, **kwargs)
        self._check_factory = check_factory
        self._runner_factory = runner_factory
        self._adapter_factory = adapter_factory
        self._fail_on_warn = fail_on_warn

    def execute(self, context: dict) -> dict:
        from dqt.algorithms._base import Verdict

        check = self._check_factory()
        runner = self._runner_factory()
        adapter = self._adapter_factory()

        result = runner.run(check, adapter)

        output = {
            "check_id": str(check.id),
            "detector_slug": result.detector_slug,
            "verdict": result.verdict.value,
            "score": result.score,
            "plain_english": result.plain_english,
        }

        if result.verdict == Verdict.fail:
            raise _DqtCheckFailed(
                f"dqt check failed: {result.detector_slug} score={result.score:.4f} — "
                f"{result.plain_english}"
            )
        if self._fail_on_warn and result.verdict == Verdict.warn:
            raise _DqtCheckFailed(
                f"dqt check warned (fail_on_warn=True): "
                f"{result.detector_slug} score={result.score:.4f}"
            )
        return output


class DqtSuiteOperator(_BaseOperator):
    """Run multiple dqt Checks as an Airflow task.

    Fails the task if any check has verdict `fail` (or `warn` when fail_on_warn=True).
    Budget-aware: uses run_suite() with the configured cost limit.

    Args:
        task_id: Airflow task identifier.
        checks_factory: Callable returning list[Check].
        runner_factory: Callable returning a Runner.
        adapter_factory: Callable returning a WarehouseAdapter.
        cost_budget_usd: Maximum total warehouse cost (default $10).
        fail_on_warn: If True, also fail when any verdict is warn.
    """

    def __init__(
        self,
        task_id: str,
        checks_factory: Callable,
        runner_factory: Callable,
        adapter_factory: Callable,
        cost_budget_usd: float = 10.0,
        fail_on_warn: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(task_id=task_id, **kwargs)
        self._checks_factory = checks_factory
        self._runner_factory = runner_factory
        self._adapter_factory = adapter_factory
        self._cost_budget_usd = cost_budget_usd
        self._fail_on_warn = fail_on_warn

    def execute(self, context: dict) -> dict:
        from dqt.algorithms._base import Verdict

        checks = self._checks_factory()
        runner = self._runner_factory()
        adapter = self._adapter_factory()

        suite = runner.run_suite(checks, adapter, cost_budget_usd=self._cost_budget_usd)

        failing = [r for r in suite.ran if r.verdict == Verdict.fail]
        warning = [r for r in suite.ran if r.verdict == Verdict.warn]

        output = {
            "n_ran": len(suite.ran),
            "n_skipped": len(suite.skipped),
            "n_fail": len(failing),
            "n_warn": len(warning),
            "budget_spent_usd": suite.budget_spent_usd,
        }

        if failing:
            slugs = ", ".join(r.detector_slug for r in failing[:5])
            raise _DqtCheckFailed(
                f"{len(failing)} dqt check(s) failed: {slugs}"
            )
        if self._fail_on_warn and warning:
            slugs = ", ".join(r.detector_slug for r in warning[:5])
            raise _DqtCheckFailed(
                f"{len(warning)} dqt check(s) warned (fail_on_warn=True): {slugs}"
            )
        return output


class _DqtCheckFailed(Exception):
    """Raised when a dqt check fails inside an Airflow operator."""
