# packages/dqt/tests/cli/test_cli_dashboard.py
import subprocess
import sys

import pytest


def _run(*args):
    return subprocess.run(
        [sys.executable, "-m", "dqt_cli.main"] + list(args),
        capture_output=True, text=True,
    )


def test_dashboard_help_lists_token_flags():
    result = _run("dashboard", "--help")
    assert result.returncode == 0
    assert "--token" in result.stdout
    assert "--generate-token" in result.stdout


def test_dashboard_help_shows_port_and_host():
    result = _run("dashboard", "--help")
    assert result.returncode == 0
    assert "--port" in result.stdout
    assert "--host" in result.stdout


def test_dashboard_generate_token_prints_64_char_hex():
    """--generate-token should always print a 64-char hex token regardless of uvicorn."""
    result = _run("dashboard", "--generate-token")
    # The token should be on the first line of stdout
    lines = result.stdout.strip().split("\n")
    token_line = lines[0]
    assert len(token_line) == 64, f"Expected 64-char token, got: {token_line!r}"
    assert all(c in "0123456789abcdef" for c in token_line)
