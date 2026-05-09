import textwrap
import pytest


VALID_YAML = textwrap.dedent("""
    checks:
      - schema_name: public
        table_name: orders
        column_name: amount
        detector_slug: completeness
        baseline:
          window_days: 14
          min_rows: 500
        sample_n: 50000

      - schema_name: public
        table_name: orders
        detector_slug: volume

      - schema_name: public
        table_name: orders
        column_name: customer_id
        detector_slug: ks_pvalue
        params:
          threshold: 0.05
""")

YAML_WITH_SCOPE = textwrap.dedent("""
    checks:
      - schema_name: public
        table_name: events
        detector_slug: completeness
        column_name: user_id
        scope:
          mode: incremental
          key_col: created_at
          since: "2024-01-01T00:00:00Z"
        filters:
          - col: status
            values: ["active", "pending"]
        sampling_pct: 10.0
""")

INVALID_YAML_MISSING_TABLE = textwrap.dedent("""
    checks:
      - schema_name: public
        column_name: amount
        detector_slug: completeness
""")

INVALID_YAML_MISSING_SLUG = textwrap.dedent("""
    checks:
      - schema_name: public
        table_name: orders
""")


def test_load_valid_yaml():
    from dqt.checks.loader import load_checks_yaml
    checks = load_checks_yaml(VALID_YAML)
    assert len(checks) == 3


def test_first_check_fields():
    from dqt.checks.loader import load_checks_yaml
    checks = load_checks_yaml(VALID_YAML)
    c = checks[0]
    assert c.schema_name == "public"
    assert c.table_name == "orders"
    assert c.column_name == "amount"
    assert c.detector_slug == "completeness"
    assert c.baseline is not None
    assert c.baseline.window_days == 14
    assert c.baseline.min_rows == 500
    assert c.sample_n == 50_000


def test_second_check_defaults():
    from dqt.checks.loader import load_checks_yaml
    checks = load_checks_yaml(VALID_YAML)
    c = checks[1]
    assert c.column_name is None
    assert c.sample_n == 100_000
    assert c.baseline is None
    assert c.filters == []
    assert c.scope is None
    assert c.sampling_pct is None


def test_third_check_params():
    from dqt.checks.loader import load_checks_yaml
    checks = load_checks_yaml(VALID_YAML)
    c = checks[2]
    assert c.params == {"threshold": 0.05}


def test_each_check_gets_unique_id():
    from dqt.checks.loader import load_checks_yaml
    checks = load_checks_yaml(VALID_YAML)
    ids = [c.id for c in checks]
    assert len(set(ids)) == len(ids)


def test_load_scope_and_filters():
    from dqt.checks.loader import load_checks_yaml
    checks = load_checks_yaml(YAML_WITH_SCOPE)
    c = checks[0]
    assert c.scope is not None
    assert c.scope.mode == "incremental"
    assert c.scope.key_col == "created_at"
    assert c.scope.since == "2024-01-01T00:00:00Z"
    assert len(c.filters) == 1
    assert c.filters[0].col == "status"
    assert set(c.filters[0].values) == {"active", "pending"}
    assert c.sampling_pct == 10.0


def test_invalid_yaml_missing_table():
    from dqt.checks.loader import load_checks_yaml, CheckValidationError
    with pytest.raises(CheckValidationError, match="table_name"):
        load_checks_yaml(INVALID_YAML_MISSING_TABLE)


def test_invalid_yaml_missing_slug():
    from dqt.checks.loader import load_checks_yaml, CheckValidationError
    with pytest.raises(CheckValidationError, match="detector_slug"):
        load_checks_yaml(INVALID_YAML_MISSING_SLUG)


def test_load_from_file(tmp_path):
    from dqt.checks.loader import load_checks_file
    p = tmp_path / "checks.yaml"
    p.write_text(VALID_YAML)
    checks = load_checks_file(str(p))
    assert len(checks) == 3
