# packages/dqt/tests/cli/test_cli_healthcheck.py
import subprocess
import sys


def test_healthcheck_exits_0():
    result = subprocess.run(
        [sys.executable, "-m", "dqt_cli.main", "healthcheck"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"healthcheck failed:\n{result.stdout}\n{result.stderr}"
    assert "healthcheck passed" in result.stdout


def test_healthcheck_in_top_level_help():
    result = subprocess.run(
        [sys.executable, "-m", "dqt_cli.main", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "healthcheck" in result.stdout
