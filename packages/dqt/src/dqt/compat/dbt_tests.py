"""Compile dqt Check objects to dbt schema YAML with native and custom test stubs.
Ref: https://docs.getdbt.com/reference/resource-configs/tests
"""
from __future__ import annotations

from collections import defaultdict

import yaml

# dqt slug → dbt native test name (direct equivalents only)
_NATIVE_MAP: dict[str, str | None] = {
    "null_fraction": "not_null",
    "uniqueness_rate": "unique",
}

# dqt slugs that map to dbt's accepted_values (need values param)
_ACCEPTED_VALUES_SLUG = "set_membership_violation"


def checks_to_dbt_yaml(checks) -> str:
    """Convert a list of Check objects to a dbt schema.yml YAML string.

    Native dbt tests (not_null, unique) are emitted as-is.
    All other detectors are emitted as dbt-tests custom test stubs with
    ``dqt_`` prefix, e.g. ``dqt_iqr_fence``.

    The caller is responsible for implementing these custom test macros
    (or using dqt's dbt integration package when available).
    """
    # Group by table
    by_table: dict[str, list] = defaultdict(list)
    for check in checks:
        by_table[f"{check.schema_name}.{check.table_name}"].append(check)

    models = []
    for fq_table, table_checks in by_table.items():
        model_name = fq_table.split(".")[-1]
        model_entry: dict = {"name": model_name, "columns": [], "tests": []}

        col_checks: dict[str, list] = defaultdict(list)
        table_level_checks = []
        for check in table_checks:
            if check.column_name:
                col_checks[check.column_name].append(check)
            else:
                table_level_checks.append(check)

        # Column-level tests
        for col_name, col_check_list in col_checks.items():
            col_entry: dict = {"name": col_name, "tests": []}
            for check in col_check_list:
                native = _NATIVE_MAP.get(check.detector_slug)
                if native:
                    col_entry["tests"].append(native)
                else:
                    test_body: dict = {f"dqt_{check.detector_slug}": {}}
                    if check.params:
                        test_body[f"dqt_{check.detector_slug}"] = dict(check.params)
                    col_entry["tests"].append(test_body)
            model_entry["columns"].append(col_entry)

        # Table-level tests
        for check in table_level_checks:
            native = _NATIVE_MAP.get(check.detector_slug)
            if native:
                model_entry["tests"].append(native)
            else:
                test_body = {f"dqt_{check.detector_slug}": dict(check.params) if check.params else {}}
                model_entry["tests"].append(test_body)

        if not model_entry["tests"]:
            del model_entry["tests"]

        models.append(model_entry)

    return yaml.dump({"version": 2, "models": models}, sort_keys=False, allow_unicode=True)
