"""dbt-dqt: run dqt quality checks after dbt model runs."""
from dqt_dbt.callback import DbtRunResult, run_checks_for_dbt_run

__all__ = ["DbtRunResult", "run_checks_for_dbt_run"]
