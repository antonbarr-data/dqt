#!/usr/bin/env bash
set -euo pipefail

# Production-like: Gunicorn with uvicorn workers.
# Uses env vars from the environment (or a .env file loaded by the caller).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/../apps/server"
exec uv run gunicorn dqt_server.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 2 \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
