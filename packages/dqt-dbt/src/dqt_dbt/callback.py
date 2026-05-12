# packages/dqt-dbt/src/dqt_dbt/callback.py
"""Run dqt checks for models that completed successfully in a dbt run.

Usage:
    from dqt_dbt import run_checks_for_dbt_run

    result = run_checks_for_dbt_run(
        run_results_path="target/run_results.json",
        runner=runner,
        adapter=adapter,
        checks=checks,
        cost_budget_usd=5.0,
    )
    print(f"Ran {len(result.suite.ran)}, skipped {len(result.suite.skipped)}")
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dqt.runner.runner import Runner, SuiteResult
    from dqt.adapters._protocol import WarehouseAdapter
    from dqt.checks.models import Check


@dataclass
class DbtRunResult:
    """Summary of the dbt-triggered dqt suite run."""
    suite: "SuiteResult"
    # Models that ran successfully in dbt (from run_results.json)
    dbt_success_models: list[str] = field(default_factory=list)
    # Checks that matched at least one successful dbt model
    matched_checks: list["Check"] = field(default_factory=list)
    # Checks skipped because no dbt model matched
    unmatched_checks: list["Check"] = field(default_factory=list)


def _load_success_models(run_results_path: str | Path) -> list[str]:
    """Extract successfully-run model names from dbt run_results.json."""
    data = json.loads(Path(run_results_path).read_text(encoding="utf-8"))
    results = data.get("results", [])
    success_models: list[str] = []
    for r in results:
        status = r.get("status", "")
        unique_id = r.get("unique_id", "")
        # Only models (node_type=model or unique_id starts with "model.")
        if status in ("success", "pass") and unique_id.startswith("model."):
            # Unique ID format: model.<project>.<model_name>
            parts = unique_id.split(".")
            if len(parts) >= 3:
                success_models.append(parts[-1])  # last segment is model name
    return success_models


def run_checks_for_dbt_run(
    runner: "Runner",
    adapter: "WarehouseAdapter",
    checks: list["Check"],
    run_results_path: str | Path = "target/run_results.json",
    cost_budget_usd: float = 10.0,
    run_all_on_missing_results: bool = False,
) -> DbtRunResult:
    """Run dqt checks for models that completed successfully in the most recent dbt run.

    Reads `run_results.json` to determine which models ran. Only checks whose
    `table_name` matches a successful dbt model name are included in the suite.
    If `run_results_path` does not exist and `run_all_on_missing_results` is True,
    all checks are run.

    Args:
        runner: Configured dqt Runner.
        adapter: WarehouseAdapter to fetch data from.
        checks: Full list of checks to filter against dbt run results.
        run_results_path: Path to dbt's run_results.json (default: target/run_results.json).
        cost_budget_usd: Cost budget passed to run_suite (default $10).
        run_all_on_missing_results: If True and run_results.json is missing, run all checks.
    """
    results_file = Path(run_results_path)

    if not results_file.exists():
        if run_all_on_missing_results:
            success_models = []
            matched = list(checks)
            unmatched: list["Check"] = []
        else:
            raise FileNotFoundError(
                f"dbt run_results.json not found at {results_file}. "
                "Pass run_all_on_missing_results=True to run all checks anyway."
            )
    else:
        success_models = _load_success_models(results_file)
        matched = [c for c in checks if c.table_name in success_models]
        unmatched = [c for c in checks if c.table_name not in success_models]

    suite = runner.run_suite(matched, adapter, cost_budget_usd=cost_budget_usd)
    return DbtRunResult(
        suite=suite,
        dbt_success_models=success_models,
        matched_checks=matched,
        unmatched_checks=unmatched,
    )
