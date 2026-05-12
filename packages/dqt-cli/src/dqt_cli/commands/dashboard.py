# packages/dqt-cli/src/dqt_cli/commands/dashboard.py
import typer


def dashboard_command(
    port: int = typer.Option(8080, "--port", "-p", help="Port to listen on"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind"),
) -> None:
    """Start the local dqt dashboard (requires dqtlib[dashboard])."""
    try:
        import uvicorn
    except ImportError:
        typer.echo(
            "Error: dqtlib[dashboard] is required. Run: pip install 'dqtlib[dashboard]'",
            err=True,
        )
        raise typer.Exit(code=1)

    from dqt.dashboard import create_app
    from dqt.store.memory import MemoryStore

    store = MemoryStore()
    app = create_app(store=store)
    typer.echo(f"dqt dashboard -> http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
