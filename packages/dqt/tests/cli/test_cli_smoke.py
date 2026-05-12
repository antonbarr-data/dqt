"""Parametrized smoke tests for every dqt CLI subcommand.

Rules:
  - Every subcommand must accept --help and exit 0.
  - Top-level --help must list every subcommand.
  - Missing required positional args must produce a non-zero exit code (not a traceback).
"""
from __future__ import annotations

import subprocess
import sys

import pytest

_CLI = [sys.executable, "-m", "dqt_cli.main"]

# Each entry: (args, expected_strings_in_output)
_SUBCOMMANDS = [
    (
        ["run", "--help"],
        ["--fit", "--output", "--watch", "--interval", "MANIFEST_PATH"],
    ),
    (
        ["dashboard", "--help"],
        ["--port", "--host", "--token", "--generate-token"],
    ),
    (
        ["list-detectors", "--help"],
        ["--group", "--plain"],
    ),
    (
        ["report", "--help"],
        ["--vault", "--out", "--title"],
    ),
    (
        ["wiki", "sync", "--help"],
        ["--model", "--force", "RAW_DIR", "WIKI_DIR"],
    ),
    (
        ["wiki", "status", "--help"],
        ["RAW_DIR", "WIKI_DIR"],
    ),
    (
        ["demo", "seed", "--help"],
        [],
    ),
    (
        ["demo", "reset", "--help"],
        [],
    ),
    (
        ["version", "--help"],
        [],
    ),
]

_SUBCOMMAND_IDS = [
    "run",
    "dashboard",
    "list-detectors",
    "report",
    "wiki-sync",
    "wiki-status",
    "demo-seed",
    "demo-reset",
    "version",
]


@pytest.mark.parametrize("args,expected_flags", _SUBCOMMANDS, ids=_SUBCOMMAND_IDS)
def test_subcommand_help_exits_0(args: list[str], expected_flags: list[str]) -> None:
    """Every subcommand --help must exit 0."""
    result = subprocess.run(_CLI + args, capture_output=True, text=True)
    assert result.returncode == 0, (
        f"'{' '.join(args)}' exited {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


@pytest.mark.parametrize("args,expected_flags", _SUBCOMMANDS, ids=_SUBCOMMAND_IDS)
def test_subcommand_help_contains_expected(args: list[str], expected_flags: list[str]) -> None:
    """--help output must mention every expected flag/argument string."""
    if not expected_flags:
        pytest.skip("no expected strings to check for this subcommand")
    result = subprocess.run(_CLI + args, capture_output=True, text=True)
    combined = result.stdout + result.stderr
    for token in expected_flags:
        assert token in combined, (
            f"'{token}' not found in help output for '{' '.join(args)}'\n"
            f"output: {combined[:600]}"
        )


def test_top_level_help_exits_0() -> None:
    """Top-level --help must exit 0."""
    result = subprocess.run(_CLI + ["--help"], capture_output=True, text=True)
    assert result.returncode == 0, (
        f"top-level --help exited {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_top_level_help_lists_all_subcommands() -> None:
    """Top-level --help must list every registered subcommand."""
    result = subprocess.run(_CLI + ["--help"], capture_output=True, text=True)
    assert result.returncode == 0
    for cmd in ["run", "dashboard", "list-detectors", "report", "wiki", "demo", "version"]:
        assert cmd in result.stdout, f"'{cmd}' missing from top-level --help"


def test_run_missing_required_arg_exits_nonzero() -> None:
    """dqt run without MANIFEST_PATH must exit non-zero, not crash."""
    result = subprocess.run(_CLI + ["run"], capture_output=True, text=True)
    assert result.returncode != 0
    assert "Traceback" not in result.stderr, (
        f"unexpected traceback:\n{result.stderr}"
    )


def test_report_missing_required_arg_exits_nonzero() -> None:
    """dqt report without --vault must exit non-zero, not crash."""
    result = subprocess.run(_CLI + ["report"], capture_output=True, text=True)
    assert result.returncode != 0
    assert "Traceback" not in result.stderr, (
        f"unexpected traceback:\n{result.stderr}"
    )


def test_wiki_sync_missing_args_exits_nonzero() -> None:
    """dqt wiki sync without positional args must exit non-zero, not crash."""
    result = subprocess.run(_CLI + ["wiki", "sync"], capture_output=True, text=True)
    assert result.returncode != 0
    assert "Traceback" not in result.stderr, (
        f"unexpected traceback:\n{result.stderr}"
    )


def test_wiki_status_missing_args_exits_nonzero() -> None:
    """dqt wiki status without positional args must exit non-zero, not crash."""
    result = subprocess.run(_CLI + ["wiki", "status"], capture_output=True, text=True)
    assert result.returncode != 0
    assert "Traceback" not in result.stderr, (
        f"unexpected traceback:\n{result.stderr}"
    )
