import yaml
import pytest

from dqt.checks.models import Check
from dqt.compat.dbt_tests import checks_to_dbt_yaml


@pytest.mark.unit
def test_compile_to_dbt_yaml():
    """iqr_fence on a numeric column compiles to a dbt custom test."""

    checks = [
        Check(schema_name="analytics", table_name="orders",
              column_name="amount", detector_slug="iqr_fence",
              params={"k": 3.0}),
        Check(schema_name="analytics", table_name="orders",
              column_name=None, detector_slug="volume_change_ratio"),
    ]
    dbt_yaml = checks_to_dbt_yaml(checks)
    data = yaml.safe_load(dbt_yaml)

    assert "models" in data
    model = data["models"][0]
    assert model["name"] == "orders"

    # Column-level test for iqr_fence
    col = next(c for c in model.get("columns", []) if c["name"] == "amount")
    test_names = [
        list(t.keys())[0] if isinstance(t, dict) else t
        for t in col["tests"]
    ]
    assert any("iqr_fence" in str(t) for t in test_names)


@pytest.mark.unit
def test_compile_null_fraction_maps_to_native_dbt():
    """null_fraction maps to dbt's built-in not_null test."""

    checks = [
        Check(schema_name="analytics", table_name="users",
              column_name="email", detector_slug="null_fraction"),
    ]
    dbt_yaml = checks_to_dbt_yaml(checks)
    data = yaml.safe_load(dbt_yaml)
    col = data["models"][0]["columns"][0]
    assert "not_null" in col["tests"]
