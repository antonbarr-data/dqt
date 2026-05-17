"""dqt metrics serve -- lightweight FastAPI app exposing the metrics API on a local port."""
from __future__ import annotations

import os
import secrets

import typer


def metrics_serve_command(
    port: int = typer.Option(8090, "--port", "-p", help="Port to listen on (default 8090)"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind"),
    token: str = typer.Option(
        None,
        "--token",
        help="Bearer token for auth (sets DQT_METRICS_TOKEN; prefer env var on shared systems)",
    ),
    generate_token: bool = typer.Option(
        False, "--generate-token", help="Generate and print a random token, then start"
    ),
    reload: bool = typer.Option(False, "--reload", help="Hot-reload on code changes (dev mode)"),
) -> None:
    """Serve the dqt metrics API on a local port."""
    if token and generate_token:
        typer.echo("Error: --token and --generate-token are mutually exclusive", err=True)
        raise typer.Exit(code=1)

    if generate_token:
        new_token = secrets.token_hex(32)
        typer.echo(new_token)
        os.environ["DQT_METRICS_TOKEN"] = new_token
    elif token:
        os.environ["DQT_METRICS_TOKEN"] = token

    try:
        import uvicorn
    except ImportError:
        typer.echo("Error: uvicorn is required. Run: pip install uvicorn", err=True)
        raise typer.Exit(code=1)

    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse

    app = FastAPI(title="dqt metrics", version="1.0")

    _token = os.environ.get("DQT_METRICS_TOKEN", "")

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        if request.url.path == "/health":
            return await call_next(request)
        if _token:
            auth = request.headers.get("Authorization", "")
            if auth != f"Bearer {_token}":
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return await call_next(request)

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "dqt-metrics"}

    try:
        from dqt.metrics import MetricRegistry
        from dqt.insights.explain import explain_movement
        from dqt.store.memory import MemoryStore
        from datetime import datetime, timedelta, timezone

        @app.get("/api/v1/metrics")
        def list_metrics():
            return [{"fqn": m.fqn, "display_name": m.display_name, "kind": m.kind}
                    for m in MetricRegistry([]).list()]

        @app.post("/api/v1/metrics/{fqn:path}/explain")
        def explain(fqn: str, lookback_days: int = 7):
            now = datetime.now(timezone.utc)
            window = (now - timedelta(days=lookback_days), now)
            store = MemoryStore()
            expl = explain_movement(fqn, window, store=store, use_llm=False)
            return {
                "metric_fqn": expl.metric_fqn,
                "summary": expl.summary_paragraph,
                "primary_channel": expl.primary_channel,
            }

    except ImportError:
        pass

    auth_note = "  (auth enabled)" if _token else "  (no auth)"
    typer.echo(f"dqt metrics -> http://{host}:{port}{auth_note}")
    uvicorn.run(app, host=host, port=port, reload=reload)
