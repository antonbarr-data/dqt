"""Every CLI subcommand must exit without crashing."""
from __future__ import annotations

import pathlib
import textwrap

import pytest
from typer.testing import CliRunner

from dqt_cli.main import app

runner = CliRunner()

# ── parametrized --help coverage ──────────────────────────────────────────────
# Add every subcommand here. The test asserts exit_code==0 and that a keyword
# appears in the help output. New commands MUST be added to this list; CI will
# catch missing entries because the command won't have a help test.

_HELP_CASES: list[tuple[list[str], str]] = [
    # command path            keyword that must appear in --help output
    (["--help"],              "dqt"),
    (["version", "--help"],   "version"),
    (["run", "--help"],       "manifest"),
    (["dashboard", "--help"], "port"),
    (["list-detectors", "--help"], "detector"),
    (["demo", "--help"],      "seed"),
    (["demo", "seed", "--help"], "seed"),
    (["demo", "reset", "--help"], "reset"),
    (["wiki", "--help"],      "sync"),
    (["wiki", "sync", "--help"], "raw"),
    (["wiki", "status", "--help"], "raw"),
    (["report", "--help"],    "vault"),
]


@pytest.mark.parametrize("cmd,keyword", _HELP_CASES, ids=[" ".join(c) for c, _ in _HELP_CASES])
def test_help_exits_cleanly(cmd: list[str], keyword: str) -> None:
    """Every subcommand --help must exit 0 and mention its key concept."""
    result = runner.invoke(app, cmd)
    assert result.exit_code == 0, f"`dqt {' '.join(cmd)}` exited {result.exit_code}:\n{result.output}"
    assert keyword.lower() in result.output.lower(), (
        f"`dqt {' '.join(cmd)}` help missing keyword {keyword!r}:\n{result.output}"
    )


# ── functional smoke tests ────────────────────────────────────────────────────

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


def test_list_detectors_plain() -> None:
    """dqt list-detectors --plain prints at least 60 slugs, one per line."""
    result = runner.invoke(app, ["list-detectors", "--plain"])
    assert result.exit_code == 0, result.output
    slugs = [line.strip() for line in result.output.splitlines() if line.strip()]
    assert len(slugs) >= 60, f"Expected >=60 detectors, got {len(slugs)}"


def test_list_detectors_group_filter() -> None:
    """dqt list-detectors --group drift returns only drift detectors."""
    result = runner.invoke(app, ["list-detectors", "--plain", "--group", "drift"])
    assert result.exit_code == 0, result.output
    slugs = [line.strip() for line in result.output.splitlines() if line.strip()]
    assert len(slugs) >= 3
    import dqt  # noqa: F401
    from dqt.algorithms._registry import registry
    for s in slugs:
        assert registry.get(s).group == "drift", f"{s} not in group 'drift'"


def test_list_detectors_help() -> None:
    """dqt list-detectors --help exits cleanly."""
    result = runner.invoke(app, ["list-detectors", "--help"])
    assert result.exit_code == 0
    assert "detector" in result.output.lower()


# ── wiki / report commands ────────────────────────────────────────────────────

def test_wiki_help() -> None:
    """dqt wiki --help exits cleanly."""
    result = runner.invoke(app, ["wiki", "--help"])
    assert result.exit_code == 0
    assert "sync" in result.output.lower()


def test_wiki_sync_help() -> None:
    """dqt wiki sync --help exits cleanly."""
    result = runner.invoke(app, ["wiki", "sync", "--help"])
    assert result.exit_code == 0
    assert "raw" in result.output.lower() or "wiki" in result.output.lower()


def test_wiki_status_help() -> None:
    """dqt wiki status --help exits cleanly."""
    result = runner.invoke(app, ["wiki", "status", "--help"])
    assert result.exit_code == 0


def test_wiki_sync_missing_raw_dir(tmp_path: pathlib.Path) -> None:
    """dqt wiki sync exits with code 1 when raw_dir does not exist."""
    result = runner.invoke(
        app, ["wiki", "sync", str(tmp_path / "nonexistent"), str(tmp_path / "wiki")]
    )
    assert result.exit_code == 1


def test_wiki_sync_empty_raw_dir(tmp_path: pathlib.Path) -> None:
    """dqt wiki sync exits cleanly with code 0 when raw_dir is empty."""
    raw = tmp_path / "raw"
    raw.mkdir()
    result = runner.invoke(app, ["wiki", "sync", str(raw), str(tmp_path / "wiki")])
    assert result.exit_code == 0
    assert "nothing" in result.output.lower() or "no documents" in result.output.lower()


def test_wiki_status_empty(tmp_path: pathlib.Path) -> None:
    """dqt wiki status runs without crashing on an empty raw + wiki dir."""
    raw = tmp_path / "raw"
    raw.mkdir()
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    result = runner.invoke(app, ["wiki", "status", str(raw), str(wiki)])
    assert result.exit_code == 0


def test_report_help() -> None:
    """dqt report --help exits cleanly."""
    result = runner.invoke(app, ["report", "--help"])
    assert result.exit_code == 0
    assert "vault" in result.output.lower()


def test_report_missing_vault(tmp_path: pathlib.Path) -> None:
    """dqt report exits with code 1 when vault dir does not exist."""
    result = runner.invoke(
        app, ["report", "--vault", str(tmp_path / "nonexistent"), "--out", str(tmp_path / "out.html")]
    )
    assert result.exit_code == 1


def test_report_empty_wiki(tmp_path: pathlib.Path) -> None:
    """dqt report exits cleanly with code 0 when wiki has no entries."""
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    result = runner.invoke(
        app, ["report", "--vault", str(wiki), "--out", str(tmp_path / "out.html")]
    )
    assert result.exit_code == 0
    assert "entries" in result.output.lower() or "no wiki" in result.output.lower()


def test_report_generates_html(tmp_path: pathlib.Path) -> None:
    """dqt report writes a valid HTML file when wiki entries are present."""
    import json
    from datetime import datetime, timezone

    wiki = tmp_path / "wiki"
    (wiki / "semantic").mkdir(parents=True)

    # Write a synthetic wiki entry
    entry_body = "> A test entry about orders.\n\n## Key Facts\n\n- fact one\n- fact two\n"
    fm = (
        "---\n"
        "id: 'abc123def456'\n"
        "title: 'Orders Table'\n"
        "kind: 'semantic'\n"
        f"generated_at: '{datetime.now(timezone.utc).isoformat()}'\n"
        "---\n"
    )
    (wiki / "semantic" / "abc123def456.md").write_text(
        fm + "# Orders Table\n\n" + entry_body, encoding="utf-8"
    )

    out = tmp_path / "report.html"
    result = runner.invoke(app, ["report", "--vault", str(wiki), "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()
    html = out.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html
    assert "Orders Table" in html
    assert "dqt" in html
