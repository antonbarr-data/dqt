"""Tests for `dqt demo seed` and `dqt demo reset` commands."""
from __future__ import annotations

import pathlib

import pytest
from typer.testing import CliRunner

from dqt_cli.main import app

runner = CliRunner()


def test_demo_seed_creates_files(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["demo", "seed"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "demo" / "fct_orders.csv").exists()
    assert (tmp_path / "demo" / "fct_sessions.csv").exists()
    assert (tmp_path / "demo" / "checks.yaml").exists()


def test_demo_seed_output_confirms_seeded(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["demo", "seed"])
    assert "not yet implemented" not in result.output
    assert result.exit_code == 0


def test_demo_seed_csv_has_rows(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["demo", "seed"])
    import pandas as pd

    orders = pd.read_csv(tmp_path / "demo" / "fct_orders.csv")
    sessions = pd.read_csv(tmp_path / "demo" / "fct_sessions.csv")
    assert len(orders) == 500
    assert len(sessions) == 500
    assert "amount_usd" in orders.columns
    assert "duration_s" in sessions.columns


def test_demo_reset_removes_demo_dir(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["demo", "seed"])
    assert (tmp_path / "demo").exists()
    result = runner.invoke(app, ["demo", "reset"])
    assert result.exit_code == 0
    assert not (tmp_path / "demo").exists()


def test_demo_reset_when_nothing_exists(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["demo", "reset"])
    assert result.exit_code == 0
    assert "Nothing" in result.output
