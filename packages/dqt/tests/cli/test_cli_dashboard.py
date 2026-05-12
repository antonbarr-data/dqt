import subprocess
import sys

import pytest


@pytest.mark.unit
def test_dashboard_help_exits_zero():
    """dqt dashboard --help must exit 0 and show --port option."""
    result = subprocess.run(
        [sys.executable, "-m", "dqt.cli.main", "dashboard", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Expected exit 0; got {result.returncode}\n{result.stderr}"
    assert "--port" in result.stdout, f"--port not in help output:\n{result.stdout}"
    assert "--host" in result.stdout, f"--host not in help output:\n{result.stdout}"


@pytest.mark.unit
def test_dashboard_missing_deps_exits_nonzero(monkeypatch):
    """dqt dashboard must exit 1 with a clear message when uvicorn is not importable."""
    import importlib
    import sys as _sys

    # Temporarily hide uvicorn from imports
    original = _sys.modules.get("uvicorn")
    _sys.modules["uvicorn"] = None  # type: ignore[assignment]
    try:
        from dqt.cli.main import _cmd_dashboard
        import argparse
        args = argparse.Namespace(host="127.0.0.1", port=8080)
        with pytest.raises(SystemExit) as exc_info:
            _cmd_dashboard(args)
        assert exc_info.value.code == 1
    finally:
        if original is None:
            _sys.modules.pop("uvicorn", None)
        else:
            _sys.modules["uvicorn"] = original
