# packages/dqt-cli/src/dqt_cli/commands/dashboard.py
import os
import secrets

import typer


def dashboard_command(
    port: int = typer.Option(8080, "--port", "-p", help="Port to listen on"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind"),
    token: str = typer.Option(
        None, "--token", help="Bearer token for auth (sets DQT_DASHBOARD_TOKEN; avoid on shared systems — prefer the env var)"
    ),
    generate_token: bool = typer.Option(
        False, "--generate-token", help="Generate and print a random bearer token, then start the dashboard"
    ),
) -> None:
    """Start the local dqt dashboard (requires dqtlib[dashboard])."""
    if token and generate_token:
        typer.echo("Error: --token and --generate-token are mutually exclusive", err=True)
        raise typer.Exit(code=1)

    if generate_token:
        new_token = secrets.token_hex(32)
        typer.echo(new_token)  # always printed first
        os.environ["DQT_DASHBOARD_TOKEN"] = new_token
    elif token:
        os.environ["DQT_DASHBOARD_TOKEN"] = token

    try:
        import uvicorn
        from dqt.dashboard import create_app
    except ImportError:
        typer.echo(
            "Error: dqtlib[dashboard] is required. Run: pip install 'dqtlib[dashboard]'",
            err=True,
        )
        raise typer.Exit(code=1)
    from dqt.store.memory import MemoryStore

    store = MemoryStore()
    app = create_app(store=store)
    auth_note = "  (auth enabled)" if os.environ.get("DQT_DASHBOARD_TOKEN") else "  (no auth)"
    typer.echo(f"dqt dashboard -> http://{host}:{port}{auth_note}")
    uvicorn.run(app, host=host, port=port)
