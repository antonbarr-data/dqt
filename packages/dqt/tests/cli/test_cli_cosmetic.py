"""Tests for CLI cosmetic improvements: P.17, P.19, P.20, P.22, P.28."""
from __future__ import annotations

import asyncio
import subprocess
import sys

import pytest

_CLI = [sys.executable, "-m", "dqt_cli.main"]


# ---------------------------------------------------------------------------
# P.19 — enhanced version command
# ---------------------------------------------------------------------------

def test_version_command_shows_python_and_platform():
    result = subprocess.run(_CLI + ["version"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "dqt" in result.stdout
    assert "Python" in result.stdout
    assert "Platform" in result.stdout


def test_version_command_shows_version_number():
    import dqt
    result = subprocess.run(_CLI + ["version"], capture_output=True, text=True)
    assert result.returncode == 0
    assert dqt.__version__ in result.stdout


# ---------------------------------------------------------------------------
# P.22 — --quiet flag present in run --help
# ---------------------------------------------------------------------------

def test_run_quiet_flag_in_help():
    result = subprocess.run(_CLI + ["run", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    combined = result.stdout + result.stderr
    assert "--quiet" in combined or "-q" in combined


# ---------------------------------------------------------------------------
# P.28 — /health returns version + uptime
# ---------------------------------------------------------------------------

def test_health_returns_version_and_uptime():
    httpx = pytest.importorskip("httpx")
    pytest.importorskip("fastapi")

    from dqt.dashboard.app import build_app
    from dqt.store.memory import MemoryStore

    app = build_app(MemoryStore())
    transport = httpx.ASGITransport(app=app)

    async def _call():
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")

    resp = asyncio.run(_call())
    assert resp.status_code == 200
    data = resp.json()
    assert "version" in data
    assert "uptime_seconds" in data
    assert isinstance(data["uptime_seconds"], (int, float))
    assert data["status"] == "ok"


def test_health_version_matches_library():
    httpx = pytest.importorskip("httpx")
    pytest.importorskip("fastapi")

    import dqt
    from dqt.dashboard.app import build_app
    from dqt.store.memory import MemoryStore

    app = build_app(MemoryStore())
    transport = httpx.ASGITransport(app=app)

    async def _call():
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")

    resp = asyncio.run(_call())
    assert resp.json()["version"] == dqt.__version__
