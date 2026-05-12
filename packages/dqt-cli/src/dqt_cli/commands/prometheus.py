# packages/dqt-cli/src/dqt_cli/commands/prometheus.py
"""dqt prometheus-exporter -- serve /metrics for Prometheus scraping."""
import typer

_console = None


def _get_console():
    global _console
    if _console is None:
        from rich.console import Console
        _console = Console()
    return _console


def prometheus_command(
    port: int = typer.Option(9100, "--port", "-p", help="Port to serve /metrics on"),
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind"),
) -> None:
    """Serve Prometheus /metrics endpoint."""
    from wsgiref.simple_server import make_server
    from dqt.store.memory import MemoryStore
    from dqt.metrics.prometheus import make_wsgi_app

    store = MemoryStore()
    app = make_wsgi_app(store)
    _get_console().print(f"dqt prometheus exporter -> http://{host}:{port}/metrics")
    with make_server(host, port, app) as httpd:
        httpd.serve_forever()
