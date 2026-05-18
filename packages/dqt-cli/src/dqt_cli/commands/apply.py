"""dqt apply -- create sources/datasets/checks/metrics from a YAML bundle."""
from __future__ import annotations

import sys
from pathlib import Path

import typer


def apply_command(
    bundle: Path = typer.Argument(..., help="Path to a dqt bundle YAML file"),
    server: str = typer.Option("http://localhost:8000", "--server", "-s", help="dqt server URL"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print what would be created without making changes"),
) -> None:
    """Apply a YAML bundle: create source, datasets, checks, and metrics via the server API."""
    try:
        import yaml
    except ImportError:
        typer.echo("pyyaml is required: pip install pyyaml", err=True)
        raise typer.Exit(1)

    try:
        import httpx
    except ImportError:
        typer.echo("httpx is required: pip install httpx", err=True)
        raise typer.Exit(1)

    if not bundle.exists():
        typer.echo(f"File not found: {bundle}", err=True)
        raise typer.Exit(1)

    with bundle.open() as f:
        data = yaml.safe_load(f)

    if data.get("apiVersion") != "dqt/v1" or data.get("kind") != "Bundle":
        typer.echo("Not a valid dqt bundle (expected apiVersion: dqt/v1, kind: Bundle)", err=True)
        raise typer.Exit(1)

    base = server.rstrip("/")

    def post(path: str, body: dict) -> dict | None:
        if dry_run:
            typer.echo(f"  [dry-run] POST {path}  {list(body.keys())}")
            return None
        try:
            r = httpx.post(f"{base}{path}", json=body, timeout=30)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as exc:
            typer.echo(f"  ERROR {path}: {exc.response.status_code} {exc.response.text}", err=True)
            return None

    # ---- source ----
    src = data.get("source", {})
    typer.echo(f"Source: {src.get('name', src.get('id', '?'))}")
    result = post("/api/v1/sources", {
        "name": src.get("name", src.get("id", "imported")),
        "engine": src.get("engine", "postgres"),
        "host": src.get("host", "localhost"),
        "port": int(src.get("port", 5432)),
        "db_name": src.get("db_name", "default"),
        "username": src.get("username", ""),
        "password": "",
        "secure": bool(src.get("secure", False)),
    })
    source_id = result.get("id") if result else src.get("id", "")

    # ---- datasets ----
    datasets = data.get("datasets", [])
    typer.echo(f"Datasets: {len(datasets)}")
    dataset_id_map: dict[str, str] = {}
    for ds in datasets:
        old_id = ds.get("id", "")
        if source_id:
            r = post("/api/v1/sources/{sid}/tables".replace("{sid}", source_id), {
                "tables": [old_id]
            })
        dataset_id_map[old_id] = old_id

    # ---- checks ----
    checks = data.get("checks", [])
    typer.echo(f"Checks: {len(checks)}")
    if checks:
        post("/api/v1/column-checks/batch", {
            "checks": [
                {
                    "dataset_id": c.get("dataset_id", ""),
                    "column_name": c.get("column", ""),
                    "detector_slug": c.get("detector", ""),
                    "params": c.get("params", {}),
                    "rationale": c.get("rationale", ""),
                }
                for c in checks
            ]
        })

    # ---- metrics ----
    metrics = data.get("metrics", [])
    typer.echo(f"Metrics: {len(metrics)}")
    if metrics:
        post("/api/v1/metrics/batch", {
            "metrics": [
                {
                    "display_name": m.get("display_name", m.get("fqn", "")),
                    "kind": m.get("kind", "ratio"),
                    "dataset": m.get("dataset", ""),
                    "description": m.get("description", ""),
                    "owners": m.get("owners", []),
                    "tags": m.get("tags", []),
                }
                for m in metrics
            ]
        })

    if dry_run:
        typer.echo("\nDry run complete -- no changes made.")
    else:
        typer.echo("\nDone.")
