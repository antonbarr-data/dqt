"""Every CLI subcommand must exit without crashing."""
from __future__ import annotations

import pathlib
import textwrap

import pytest
from typer.testing import CliRunner

from dqt_cli.main import app

runner = CliRunner()


def test_version_prints_something() -> None:
    """Test that `dqt version` prints something and exits cleanly."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert len(result.output.strip()) > 0


def test_demo_seed_and_reset(tmp_path: pathlib.Path, monkeypatch) -> None:
    """Test that `dqt demo seed` and `dqt demo reset` exit cleanly."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["demo", "seed"])
    assert result.exit_code == 0, result.output
    result = runner.invoke(app, ["demo", "reset"])
    assert result.exit_code == 0


def test_run_valid_manifest(tmp_path: pathlib.Path) -> None:
    """Test that `dqt run` with a valid manifest exits cleanly."""
    import duckdb

    db_path = tmp_path / "test.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute("CREATE TABLE t (amount DOUBLE)")
    conn.execute("INSERT INTO t VALUES (1.0), (2.0), (3.0)")
    conn.close()

    db_path_str = db_path.as_posix()
    manifest = tmp_path / "checks.yaml"
    manifest.write_text(
        textwrap.dedent(
            f"""\
            version: "1"
            source:
              type: duckdb
              id: t
              database: "{db_path_str}"
            checks:
              - schema_name: main
                table_name: t
                column_name: amount
                detector_slug: null_fraction
            """
        )
    )
    result = runner.invoke(app, ["run", str(manifest)])
    # 0 = all checks pass; 2 = checks fail; both are valid exits
    assert result.exit_code in (0, 2), result.output


def test_run_missing_manifest() -> None:
    """Test that `dqt run` with a missing manifest exits with error."""
    result = runner.invoke(app, ["run", "nonexistent_manifest_xyz.yaml"])
    assert result.exit_code != 0


def test_dashboard_help() -> None:
    """Test that `dqt dashboard --help` shows help text."""
    result = runner.invoke(app, ["dashboard", "--help"])
    assert result.exit_code == 0
    assert "port" in result.output.lower() or "host" in result.output.lower()


def test_run_help() -> None:
    """Test that `dqt run --help` shows help text."""
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "manifest" in result.output.lower() or "checks" in result.output.lower()


def test_demo_help() -> None:
    """Test that `dqt demo --help` shows help text."""
    result = runner.invoke(app, ["demo", "--help"])
    assert result.exit_code == 0
    assert "seed" in result.output.lower() or "reset" in result.output.lower()


def test_version_help() -> None:
    """Test that `dqt version --help` shows help text."""
    result = runner.invoke(app, ["version", "--help"])
    assert result.exit_code == 0
    assert "version" in result.output.lower()
