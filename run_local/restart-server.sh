#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Kill any process using port 8000
echo "Stopping any process on port 8000..."
if command -v fuser &>/dev/null; then
  fuser -k 8000/tcp 2>/dev/null || true
else
  # WSL / Git Bash fallback
  pid=$(netstat -tlnp 2>/dev/null | awk '/:8000 /{split($NF,a,"/"); print a[1]}')
  [ -n "$pid" ] && kill "$pid" 2>/dev/null || true
fi
sleep 1

echo "Starting dqt backend (dev, --reload)..."
cd "${REPO_ROOT}/apps/server"
exec uv run uvicorn dqt_server.main:app --reload --host 0.0.0.0 --port 8000
