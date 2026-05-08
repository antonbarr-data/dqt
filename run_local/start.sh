#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "Starting dqt local stack..."

docker compose -f "${SCRIPT_DIR}/docker-compose.yml" up -d

echo -n "Waiting for Postgres..."
until docker compose -f "${SCRIPT_DIR}/docker-compose.yml" exec -T postgres \
  pg_isready -U dqt -d dqt > /dev/null 2>&1; do
  echo -n "."
  sleep 1
done
echo " ready."

echo -n "Waiting for Redis..."
until docker compose -f "${SCRIPT_DIR}/docker-compose.yml" exec -T redis \
  redis-cli ping 2>/dev/null | grep -q PONG; do
  echo -n "."
  sleep 1
done
echo " ready."

echo ""
echo "Stack running:"
echo "  Postgres  -> localhost:5434  (user: dqt, pass: dqtdev, db: dqt)"
echo "  Redis     -> localhost:6379"
echo "  MailHog   -> http://localhost:8025"
echo "  Adminer   -> http://localhost:8081"
echo ""
echo "Next: make db-migrate && make dev-server && make dev-web"
