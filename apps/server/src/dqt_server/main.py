"""dqt FastAPI service — main entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="dqt API",
    version="0.1.0",
    description="Data quality, observability, semantic, and causality service",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok", "service": "dqt-server"}


@app.get("/api/v1/ping", tags=["ops"])
def ping() -> dict:
    return {"pong": True}
