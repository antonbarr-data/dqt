#!/usr/bin/env bash
# dqt local environment initialiser.
# Run once on a clean machine after cloning the repo.
#
# Prerequisites:
#   - Docker Desktop (or compatible Docker runtime)
#   - uv  (https://docs.astral.sh/uv/getting-started/installation/)
#   - Node 18+ and pnpm  (https://pnpm.io/installation)
#
# Usage:
#   ./setup/init_local.sh
#   Follow the prompts — secrets are written to .env automatically.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

step()  { echo -e "\n${GREEN}==> $*${NC}"; }
info()  { echo -e "  ${CYAN}$*${NC}"; }
warn()  { echo -e "${YELLOW}WARN: $*${NC}"; }
abort() { echo -e "${RED}ERROR: $*${NC}" >&2; exit 1; }

# ─── prerequisites ───────────────────────────────────────────────────────────
step "Checking prerequisites"

command -v docker >/dev/null 2>&1 || abort "Docker not found. Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
command -v uv     >/dev/null 2>&1 || abort "uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
command -v pnpm   >/dev/null 2>&1 || abort "pnpm not found. Install: npm install -g pnpm"
command -v python3 >/dev/null 2>&1 || abort "python3 not found. Install Python 3.12+ from https://python.org"

echo "  docker $(docker --version | awk '{print $3}' | tr -d ',')"
echo "  uv     $(uv --version)"
echo "  pnpm   $(pnpm --version)"
echo "  python $(python3 --version)"

ENV_FILE="$REPO_ROOT/.env"

# ─── .env helpers ─────────────────────────────────────────────────────────────

# Read current value of a key from .env (empty string if absent/unset)
get_env() {
  local key="$1"
  grep "^${key}=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- || true
}

# Write or update a key in .env
set_env() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    # In-place replacement — escape special chars in value for sed
    local escaped
    escaped=$(printf '%s\n' "$value" | sed 's/[[\.*^$()+?{|]/\\&/g')
    sed -i.bak "s|^${key}=.*|${key}=${escaped}|" "$ENV_FILE" && rm -f "${ENV_FILE}.bak"
  else
    printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
  fi
}

# ─── bootstrap .env from local.env ───────────────────────────────────────────
step "Setting up .env"

if [[ ! -f "$ENV_FILE" ]]; then
  info "Creating .env from .env.example..."
  cp "$REPO_ROOT/.env.example" "$ENV_FILE"
  info ".env created."
else
  info ".env already exists — will fill in any missing values."
fi

# ─── required secrets ────────────────────────────────────────────────────────
step "Configuring required secrets"

echo -e "  Secrets are written to ${CYAN}.env${NC}. Press Enter to auto-generate where offered."
echo ""

prompt_required() {
  local key="$1"
  local description="$2"
  local autogen_cmd="${3:-}"

  local current
  current=$(get_env "$key")
  if [[ -n "$current" ]]; then
    info "$key  ✓  already set"
    return
  fi

  echo -e "  ${CYAN}${key}${NC}"
  echo -e "  ${description}"

  local value=""
  if [[ -n "$autogen_cmd" ]]; then
    echo -n "  [Enter] auto-generate  or  type value: "
    read -r value
    if [[ -z "$value" ]]; then
      value=$(eval "$autogen_cmd")
      info "Generated: ${value}"
    fi
  else
    echo -n "  Value: "
    read -r value
    while [[ -z "$value" ]]; do
      warn "Cannot be empty."
      echo -n "  Value: "
      read -r value
    done
  fi

  set_env "$key" "$value"
  echo ""
}

prompt_required "JWT_SECRET_KEY" \
  "JWT signing key for auth tokens." \
  'python3 -c "import secrets; print(secrets.token_hex(32))"'

prompt_required "ANTHROPIC_API_KEY" \
  "Anthropic API key — get from: https://console.anthropic.com/"

prompt_required "DQT_CREDS_KEY" \
  "Warehouse credential encryption key." \
  'python3 -c "import os,base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"'

# ─── super-admin account ──────────────────────────────────────────────────────
step "Super-admin account"
echo -e "  Created on first server start if the email is not already in the database."
echo ""

prompt_required "ADMIN_EMAIL" \
  "Email address for the default sysadmin account." \
  'echo "admin@localhost"'

prompt_required "ADMIN_PASSWORD" \
  "Password for the default sysadmin account (used for email/password login)." \
  'python3 -c "import secrets; print(secrets.token_urlsafe(16))"'

# ─── optional: Google OAuth ───────────────────────────────────────────────────
echo ""
echo -e "  ${YELLOW}Optional: Google OAuth (social login). Press Enter to skip.${NC}"
echo ""

prompt_optional() {
  local key="$1"
  local description="$2"
  local default_val="${3:-}"

  local current
  current=$(get_env "$key")
  if [[ -n "$current" ]]; then
    info "$key  ✓  already set"
    return
  fi

  echo -e "  ${CYAN}${key}${NC}  ${description}"
  echo -n "  Value [skip]: "
  read -r value
  if [[ -n "$value" ]]; then
    set_env "$key" "$value"
    info "Set."
  elif [[ -n "$default_val" ]]; then
    set_env "$key" "$default_val"
    info "Using default: ${default_val}"
  fi
  echo ""
}

prompt_optional "GOOGLE_CLIENT_ID"     "Google OAuth client ID"
GCID=$(get_env "GOOGLE_CLIENT_ID")
if [[ -n "$GCID" ]]; then
  prompt_optional "GOOGLE_CLIENT_SECRET" "Google OAuth client secret"
  prompt_optional "GOOGLE_REDIRECT_URI"  "OAuth redirect URI" \
    "http://localhost:8000/api/v1/auth/google/callback"
fi

# ─── DATABASE_URL ─────────────────────────────────────────────────────────────
step "Database connection"

DEFAULT_DB_URL="postgresql+asyncpg://dqt:dqtdev@localhost:5434/dqt"
CURRENT_DB_URL=$(get_env "DATABASE_URL")
if [[ -z "$CURRENT_DB_URL" ]]; then
  set_env "DATABASE_URL" "$DEFAULT_DB_URL"
  CURRENT_DB_URL="$DEFAULT_DB_URL"
fi

echo -e "  Current DATABASE_URL: ${CYAN}${CURRENT_DB_URL}${NC}"
echo -n "  Press Enter to keep, or type a replacement: "
read -r new_db_url
if [[ -n "$new_db_url" ]]; then
  set_env "DATABASE_URL" "$new_db_url"
  CURRENT_DB_URL="$new_db_url"
  info "DATABASE_URL updated."
fi

# ─── docker stack ─────────────────────────────────────────────────────────────
step "Starting Docker services (Postgres, Redis, MailHog, Adminer)"

docker compose -f "$REPO_ROOT/run_local/docker-compose.yml" up -d

echo -n "  Waiting for Postgres"
n=0
until docker compose -f "$REPO_ROOT/run_local/docker-compose.yml" exec -T postgres \
    pg_isready -U dqt -d dqt >/dev/null 2>&1; do
  echo -n "."; sleep 1
  (( ++n >= 60 )) && abort "Postgres did not become ready after 60s"
done
echo " ready"

echo -n "  Waiting for Redis"
n=0
until docker compose -f "$REPO_ROOT/run_local/docker-compose.yml" exec -T redis \
    redis-cli ping 2>/dev/null | grep -q PONG; do
  echo -n "."; sleep 1
  (( ++n >= 30 )) && abort "Redis did not become ready after 30s"
done
echo " ready"

# ─── verify DATABASE_URL connection ──────────────────────────────────────────
step "Verifying database connection"

# Strip the asyncpg dialect prefix for testing
TEST_URL="${CURRENT_DB_URL/postgresql+asyncpg:\/\//postgresql:\/\/}"

echo -n "  Connecting to: ${CURRENT_DB_URL} ... "

DB_OK=false
if command -v psql >/dev/null 2>&1; then
  if psql "$TEST_URL" -c "SELECT 1;" >/dev/null 2>&1; then
    DB_OK=true
  fi
else
  # Fall back to pure Python (no external packages needed)
  if python3 - "$TEST_URL" <<'PYEOF' 2>/dev/null
import sys, socket, urllib.parse
raw = sys.argv[1]
p = urllib.parse.urlparse(raw)
host = p.hostname or "localhost"
port = p.port or 5432
try:
    s = socket.create_connection((host, port), timeout=5)
    s.close()
except Exception as e:
    sys.exit(1)
PYEOF
  then
    DB_OK=true
  fi
fi

if [[ "$DB_OK" == "true" ]]; then
  echo "ok"
else
  echo ""
  abort "Cannot connect to database: ${CURRENT_DB_URL}
  Check that the host, port, credentials, and database name are correct.
  Edit .env and re-run this script to retry."
fi

# ─── Python dependencies ──────────────────────────────────────────────────────
step "Installing Python dependencies (uv sync)"

uv sync --all-packages

# ─── Node dependencies ────────────────────────────────────────────────────────
step "Installing Node dependencies (pnpm install)"

cd "$REPO_ROOT/apps/web" && pnpm install --frozen-lockfile
cd "$REPO_ROOT"

# ─── demo seed ────────────────────────────────────────────────────────────────
step "Seeding demo data"

uv run dqt demo seed

# ─── done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}Done! Local environment is ready.${NC}"
echo ""
echo "  Services:"
echo "    Postgres  -> localhost:5434  (user: dqt, pass: dqtdev, db: dqt)"
echo "    Redis     -> localhost:6379"
echo "    MailHog   -> http://localhost:8025"
echo "    Adminer   -> http://localhost:8081"
echo ""
echo "  Start development servers (in separate terminals or tmux):"
echo "    make dev-server   -- FastAPI on http://localhost:8000"
echo "    make dev-web      -- Next.js on http://localhost:3000"
echo "    make dev-worker   -- arq background worker (optional)"
echo ""
echo "  Or start everything at once:"
echo "    make dev"
