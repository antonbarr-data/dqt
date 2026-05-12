# packages/dqt-dagster/src/dqt_dagster/resources.py
"""Dagster resource and helper for dqt.

DqtResource  — a configurable Dagster resource that holds the Runner + adapter
run_dqt_checks() — helper to call from an @asset or @op, raises AssetMaterializationError
                   on failures so Dagster marks the step as failed

Usage:
    from dagster import asset, Definitions
    from dqt_dagster import DqtResource

    @asset
    def orders(dqt_resource: DqtResource):
        ...  # your asset logic
        dqt_resource.run_checks_for(table="orders")

    defs = Definitions(
        assets=[orders],
        resources={"dqt_resource": DqtResource(
            runner_factory=build_runner,
            adapter_factory=build_adapter,
            checks=ALL_CHECKS,
        )},
    )
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from dqt.runner.runner import Runner, SuiteResult
    from dqt.adapters._protocol import WarehouseAdapter
    from dqt.checks.models import Check


@dataclass
class DqtResource:
    """Dagster resource wrapping a dqt Runner and WarehouseAdapter.

    Args:
        runner_factory: Callable() -> Runner. Called lazily per use.
        adapter_factory: Callable() -> WarehouseAdapter. Called lazily per use.
        checks: All available Check definitions.
        cost_budget_usd: Default cost budget for run_suite (default $10).
    """
    runner_factory: Callable
    adapter_factory: Callable
    checks: list = field(default_factory=list)
    cost_budget_usd: float = 10.0

    def run_checks_for(
        self,
        table: str,
        cost_budget_usd: float | None = None,
        fail_on_warn: bool = False,
    ) -> "SuiteResult":
        """Run all checks whose table_name matches `table`.

        Raises DqtAssetCheckFailed if any check has verdict fail (or warn when
        fail_on_warn=True). Suitable for calling inside an @asset or @op.
        """
        from dqt.algorithms._base import Verdict
        matching = [c for c in self.checks if c.table_name == table]
        return run_dqt_checks(
            checks=matching,
            runner=self.runner_factory(),
            adapter=self.adapter_factory(),
            cost_budget_usd=cost_budget_usd if cost_budget_usd is not None else self.cost_budget_usd,
            fail_on_warn=fail_on_warn,
        )

    def run_suite(
        self,
        checks: list | None = None,
        cost_budget_usd: float | None = None,
    ) -> "SuiteResult":
        """Run a suite of checks (defaults to self.checks)."""
        return run_dqt_checks(
            checks=checks if checks is not None else self.checks,
            runner=self.runner_factory(),
            adapter=self.adapter_factory(),
            cost_budget_usd=cost_budget_usd if cost_budget_usd is not None else self.cost_budget_usd,
        )


def run_dqt_checks(
    checks: list["Check"],
    runner: "Runner",
    adapter: "WarehouseAdapter",
    cost_budget_usd: float = 10.0,
    fail_on_warn: bool = False,
) -> "SuiteResult":
    """Run a suite of dqt checks and raise on any failures.

    Raises DqtAssetCheckFailed (a subclass of Exception) so Dagster marks the
    step as failed and surfaces the failing check details in the event log.
    """
    from dqt.algorithms._base import Verdict

    suite = runner.run_suite(checks, adapter, cost_budget_usd=cost_budget_usd)

    failing = [r for r in suite.ran if r.verdict == Verdict.fail]
    warning = [r for r in suite.ran if r.verdict == Verdict.warn]

    if failing:
        details = "; ".join(
            f"{r.detector_slug}={r.score:.4f}" for r in failing[:5]
        )
        raise DqtAssetCheckFailed(
            f"{len(failing)} dqt check(s) failed: {details}"
        )
    if fail_on_warn and warning:
        details = "; ".join(
            f"{r.detector_slug}={r.score:.4f}" for r in warning[:5]
        )
        raise DqtAssetCheckFailed(
            f"{len(warning)} dqt check(s) warned (fail_on_warn=True): {details}"
        )
    return suite


class DqtAssetCheckFailed(Exception):
    """Raised when a dqt check fails inside a Dagster asset or op."""
