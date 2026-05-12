from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from dqt.checks.models import Check
from dqt.runner.runner import Runner
from dqt.store.memory import MemoryStore

from dqt_cli.adapter_factory import build_adapter
from dqt_cli.manifest import load_manifest

console = Console()


def run_command(
    manifest_path: Path = typer.Argument(..., help="Path to the YAML manifest file"),
    fit: bool = typer.Option(True, "--fit/--no-fit", help="Fit baselines before scoring"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table | json"),
    watch: bool = typer.Option(False, "--watch", help="Re-run checks on a schedule"),
    interval: float = typer.Option(60.0, "--interval", help="Seconds between watch runs"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output except errors"),
    max_runs: Optional[int] = typer.Option(
        None, "--max-runs", hidden=True, help="Maximum number of runs (for testing)"
    ),
) -> None:
    """Run data quality checks defined in a YAML manifest."""
    runs = 0
    while True:
        exit_code = _run_once(manifest_path, fit, output, quiet=quiet)
        runs += 1
        if max_runs is not None and runs >= max_runs:
            raise typer.Exit(code=exit_code)
        if not watch:
            raise typer.Exit(code=exit_code)
        if not quiet:
            console.print(f"  watching — next run in {interval:.0f}s (Ctrl+C to stop)")
        time.sleep(interval)


def _run_once(
    manifest_path: Path, fit: bool = True, output: str = "table", *, quiet: bool = False
) -> int:
    """Execute checks once, return exit code (0 or 2)."""
    if not manifest_path.exists():
        console.print(f"[red]Error:[/red] manifest file not found: {manifest_path}")
        return 1

    manifest = load_manifest(str(manifest_path))
    adapter = build_adapter(manifest.source)

    try:
        checks = [Check.model_validate(raw) for raw in manifest.checks]
    except Exception as exc:
        console.print(f"[red]Error loading checks:[/red] {exc}")
        return 1

    if not checks:
        if not quiet:
            console.print("[yellow]No checks defined in manifest.[/yellow]")
        return 0

    store = MemoryStore()
    runner = Runner(store)

    results = []
    for check in checks:
        try:
            if fit:
                runner.fit(check, adapter)
            result = runner.run(check, adapter)
            results.append((check, result))
        except Exception as exc:
            results.append((check, exc))

    if not quiet:
        if output == "json":
            import json

            out = []
            for check, result in results:
                if isinstance(result, Exception):
                    out.append({"check": check.detector_slug, "error": str(result)})
                else:
                    out.append(
                        {
                            "check": check.detector_slug,
                            "table": f"{check.schema_name}.{check.table_name}",
                            "column": check.column_name,
                            "verdict": result.verdict.value,
                            "score": result.score,
                            "plain_english": result.plain_english,
                        }
                    )
            # Use plain print to avoid Rich ANSI codes polluting JSON output
            print(json.dumps(out, indent=2))
        else:
            _print_table(results)

    any_fail = any(
        isinstance(r, Exception) or r.verdict.value in ("fail",) for _, r in results
    )
    return 2 if any_fail else 0


def _print_table(results: list) -> None:
    table = Table(title="DQ Check Results", show_lines=True)
    table.add_column("Table", style="cyan")
    table.add_column("Column", style="cyan")
    table.add_column("Detector", style="cyan")
    table.add_column("Verdict", justify="center")
    table.add_column("Score", justify="right")
    table.add_column("Summary")

    verdict_style = {"pass": "green", "warn": "yellow", "fail": "red"}

    for check, result in results:
        col = check.column_name or "(table)"
        tbl = f"{check.schema_name}.{check.table_name}"
        if isinstance(result, Exception):
            table.add_row(tbl, col, check.detector_slug, "[red]ERROR[/red]", "—", str(result))
        else:
            style = verdict_style.get(result.verdict.value, "white")
            table.add_row(
                tbl,
                col,
                check.detector_slug,
                f"[{style}]{result.verdict.value.upper()}[/{style}]",
                f"{result.score:.4f}",
                result.plain_english,
            )

    console.print(table)
