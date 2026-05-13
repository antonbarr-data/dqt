# packages/dqt/tests/cli/test_cli_main.py
"""Tests for the in-wheel argparse CLI (dqt.cli.main)."""
import subprocess
import sys

_CLI = [sys.executable, "-m", "dqt.cli.main"]


def test_wiki_sync_in_help():
    result = subprocess.run(_CLI + ["wiki", "sync", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "RAW_DIR" in result.stdout or "raw_dir" in result.stdout.lower() or "raw-dir" in result.stdout.lower()


def test_wiki_status_in_help():
    result = subprocess.run(_CLI + ["wiki", "status", "--help"], capture_output=True, text=True)
    assert result.returncode == 0


def test_dashboard_token_in_help():
    result = subprocess.run(_CLI + ["dashboard", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "--token" in result.stdout


def test_dashboard_generate_token_in_help():
    result = subprocess.run(_CLI + ["dashboard", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "--generate-token" in result.stdout
