import json
import subprocess
import sys
import textwrap

import pandas as pd
import pytest
from xml.etree import ElementTree


@pytest.fixture()
def csv_and_checks(tmp_path):
    """Create a CSV file and a checks YAML pointing at it."""
    csv_path = tmp_path / "orders.csv"
    pd.DataFrame({"amount": list(range(100))}).to_csv(csv_path, index=False)

    checks_yaml = tmp_path / "checks.yaml"
    checks_yaml.write_text(textwrap.dedent(f"""\
        checks:
          - schema_name: default
            table_name: orders
            column_name: amount
            detector_slug: iqr_fence
    """))
    return csv_path, checks_yaml


def test_run_with_local_adapter_json_output(csv_and_checks):
    """dqt run --connection file://... checks.yaml --output json exits 0 and emits JSON."""
    csv_path, checks_yaml = csv_and_checks

    result = subprocess.run(
        [sys.executable, "-m", "dqt.cli.main", "run",
         str(checks_yaml),
         "--connection", f"file://{csv_path}",
         "--output", "json"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert "results" in data
    assert len(data["results"]) == 1


def test_run_with_local_adapter_junit_output(csv_and_checks):
    """dqt run --output junit emits valid JUnit XML."""
    csv_path, checks_yaml = csv_and_checks

    result = subprocess.run(
        [sys.executable, "-m", "dqt.cli.main", "run",
         str(checks_yaml),
         "--connection", f"file://{csv_path}",
         "--output", "junit"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    root = ElementTree.fromstring(result.stdout.split('\n', 1)[1] if result.stdout.startswith('<?xml') else result.stdout)
    assert root.tag == "testsuites"
    assert len(root.findall(".//testcase")) >= 1


def test_run_without_connection_prints_note(csv_and_checks):
    """dqt run without --connection prints a note, does not crash."""
    _, checks_yaml = csv_and_checks

    result = subprocess.run(
        [sys.executable, "-m", "dqt.cli.main", "run", str(checks_yaml)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "Note:" in result.stdout
