"""Tests for `dqt run` command using an in-memory DuckDB source."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dqt_cli.main import app

runner = CliRunner()


@pytest.fixture
def tmp_manifest(tmp_path: Path) -> Path:
    """Write a minimal manifest with a DuckDB in-memory source + one check."""
    manifest_content = textwrap.dedent("""\
        version: "1"

        source:
          type: duckdb
          id: test
          database: ":memory:"

        checks:
          - schema_name: main
            table_name: orders
            column_name: amount
            detector_slug: mad_outlier_fraction
    """)
    mf = tmp_path / "manifest.yaml"
    mf.write_text(manifest_content)
    return mf


def test_run_missing_manifest():
    result = runner.invoke(app, ["run", "nonexistent.yaml"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower() or "Error" in result.output


def test_run_empty_checks(tmp_path: Path):
    mf = tmp_path / "empty.yaml"
    mf.write_text("version: '1'\nsource:\n  type: duckdb\n  database: ':memory:'\nchecks: []\n")
    result = runner.invoke(app, ["run", str(mf)])
    assert result.exit_code == 0
    assert "No checks" in result.output


def test_run_produces_table_output(tmp_path: Path):
    """Run against a real in-memory DuckDB file with data."""
    import duckdb

    db_path = tmp_path / "test.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute("CREATE TABLE orders (amount DOUBLE, status VARCHAR)")
    conn.execute("INSERT INTO orders VALUES (10.0, 'active'), (20.0, NULL), (30.0, 'active')")
    conn.close()

    # Use forward slashes so YAML does not interpret backslashes as escape sequences
    db_path_str = db_path.as_posix()
    mf = tmp_path / "manifest.yaml"
    mf.write_text(
        f"""\
version: "1"
source:
  type: duckdb
  id: test
  database: "{db_path_str}"
checks:
  - schema_name: main
    table_name: orders
    column_name: amount
    detector_slug: mad_outlier_fraction
"""
    )
    result = runner.invoke(app, ["run", str(mf)])
    # Should exit 0 (all pass) or 2 (fail verdict)
    assert result.exit_code in (0, 2)
    assert "mad_outlier_fraction" in result.output or "PASS" in result.output or "FAIL" in result.output


def test_run_json_output(tmp_path: Path):
    """JSON output format includes verdict and score fields."""
    import duckdb
    import json

    db_path = tmp_path / "test.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute("CREATE TABLE sales (revenue DOUBLE)")
    conn.execute("INSERT INTO sales VALUES (100.0), (200.0), (300.0)")
    conn.close()

    db_path_str = db_path.as_posix()
    mf = tmp_path / "manifest.yaml"
    mf.write_text(
        f"""\
version: "1"
source:
  type: duckdb
  id: test
  database: "{db_path_str}"
checks:
  - schema_name: main
    table_name: sales
    column_name: revenue
    detector_slug: mad_outlier_fraction
"""
    )
    result = runner.invoke(app, ["run", str(mf), "--output", "json"])
    assert result.exit_code in (0, 2)
    # Output should contain valid JSON
    output_text = result.output.strip()
    parsed = json.loads(output_text)
    assert isinstance(parsed, list)
    assert len(parsed) == 1
    assert "verdict" in parsed[0]
    assert "score" in parsed[0]


def test_run_no_fit(tmp_path: Path):
    """--no-fit should still produce results (runner auto-fits on first run)."""
    import duckdb

    db_path = tmp_path / "test.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute("CREATE TABLE events (value DOUBLE)")
    conn.execute("INSERT INTO events VALUES (1.0), (2.0), (3.0)")
    conn.close()

    db_path_str = db_path.as_posix()
    mf = tmp_path / "manifest.yaml"
    mf.write_text(
        f"""\
version: "1"
source:
  type: duckdb
  id: test
  database: "{db_path_str}"
checks:
  - schema_name: main
    table_name: events
    column_name: value
    detector_slug: mad_outlier_fraction
"""
    )
    result = runner.invoke(app, ["run", str(mf), "--no-fit"])
    assert result.exit_code in (0, 2)
    assert "mad_outlier_fraction" in result.output or "PASS" in result.output or "FAIL" in result.output
