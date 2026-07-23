# dqt Makefile — single entry point for dev tasks.
# uv handles Python; pnpm handles the web app.

.PHONY: help install gen gen-check stats-scales engines types openapi \
        lint lint-py lint-web format typecheck \
        test test-lib test-adapters test-server-unit test-server-int test-e2e \
        dev dev-server dev-worker dev-web \
        build clean reset \
        db-migrate db-revision db-er \
        demo demo-seed demo-reset \
        publish-rc publish

# ─── help ───────────────────────────────────────────────────────────
help:
	@echo "Common targets:"
	@echo "  make install          — uv sync + pnpm install"
	@echo "  make gen              — regenerate enums, scales, engines, types, openapi"
	@echo "  make lint             — ruff + mypy + eslint + tsc"
	@echo "  make test-lib         — library tests (must pass in <60s)"
	@echo "  make test             — full test suite"
	@echo "  make dev              — server + worker + web with hot reload"
	@echo "  make demo             — start local stack with demo data"
	@echo "  make db-schema        — print ORM DDL to stdout for drift comparison (does not overwrite schema.sql)"
	@echo ""
	@echo "Codegen:"
	@echo "  make stats-scales     — Python STAT_SCALES → TS"
	@echo "  make engines          — adapter configs → TS engines.ts"
	@echo "  make openapi          — server's OpenAPI spec"
	@echo "  make types            — OpenAPI → TS types"

# ─── install ────────────────────────────────────────────────────────
install:
	uv sync --all-packages
	cd apps/web && pnpm install --frozen-lockfile

# ─── codegen ────────────────────────────────────────────────────────
gen: stats-scales engines openapi types
	uv run python shared/generators/enums_to_python.py
	uv run python shared/generators/enums_to_ts.py

stats-scales:
	uv run python shared/generators/scales_to_ts.py

engines:
	uv run python shared/generators/engines_to_ts.py

openapi:
	uv run python -m dqt_server.scripts.dump_openapi > apps/server/openapi.json

types: openapi
	cd apps/web && pnpm exec openapi-typescript ../../apps/server/openapi.json -o src/generated/api.ts

gen-check:
	@./shared/generators/check_drift.sh

# ─── lint / format / typecheck ──────────────────────────────────────
lint: lint-py lint-web

lint-py:
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy packages/dqt/src apps/server/src apps/worker/src

lint-web:
	cd apps/web && pnpm lint
	cd apps/web && pnpm exec tsc --noEmit

format:
	uv run ruff format .
	uv run ruff check --fix .
	cd apps/web && pnpm format

typecheck: lint-py
	cd apps/web && pnpm exec tsc --noEmit

# ─── tests ──────────────────────────────────────────────────────────
test: test-lib test-server-unit test-server-int

test-lib:
	uv run pytest packages/dqt/tests -m "not adapter and not slow" --maxfail=1

test-adapters:
	uv run pytest packages/dqt/tests/adapters -m adapter

test-server-unit:
	./tests/run_unit_tests.sh

test-server-int:
	./tests/run_integration_tests.sh

test-e2e:
	./tests/run_e2e_tests.sh

# ─── dev ────────────────────────────────────────────────────────────
dev:
	@./run_local/start.sh
	@echo "Stack ready. Run dev-server, dev-worker, dev-web in separate terminals (or 'make dev-all')."

dev-server:
	cd apps/server && uv run uvicorn dqt_server.main:app --reload --port 8000

dev-worker:
	cd apps/worker && uv run arq dqt_worker.main.WorkerSettings

dev-web:
	cd apps/web && pnpm dev

# ─── build ──────────────────────────────────────────────────────────
build:
	uv build --package dqt --package dqt-cli
	cd apps/web && pnpm build

# ─── reset / clean ──────────────────────────────────────────────────
clean:
	rm -rf packages/*/dist packages/*/build packages/*/*.egg-info
	rm -rf apps/web/.next apps/web/node_modules/.cache
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov

reset: clean
	./run_local/stop.sh
	docker compose -f run_local/docker-compose.yml down -v

# ─── DB ─────────────────────────────────────────────────────────────
db-schema:
	@# Emit the ORM-only DDL to stdout for comparison — does NOT overwrite schema.sql.
	@# schema.sql is the authoritative production schema; edit it by hand.
	@cd apps/server && uv run python -c "\
import sys; sys.path.insert(0,'src'); \
from dqt_server.main import _load_dotenv; _load_dotenv(); \
from sqlalchemy.dialects import postgresql; \
from sqlalchemy.schema import CreateTable, CreateIndex; \
from dqt_server.db.engine import Base; \
from dqt_server.models import ref_data as _; \
from dqt_server.auth.models import User; \
lines = ['-- ORM-generated DDL (for drift comparison only — not the authoritative schema)', '']; \
[lines.extend([str(CreateTable(t).compile(dialect=postgresql.dialect())).strip()+';','']) \
for t in Base.metadata.sorted_tables]; \
print('\n'.join(lines))"

db-migrate:
	@echo "This project does not use Alembic. Schema is managed by SQLAlchemy create_all on server startup."
	@echo "Run: make dev-server"

db-revision:
	@echo "This project does not use Alembic migrations."

db-er:
	uv run python shared/generators/er_diagram.py > docs/architecture/er.svg

# ─── demo ───────────────────────────────────────────────────────────
demo: install
	./run_local/start.sh
	$(MAKE) demo-seed

demo-seed:
	uv run dqt demo seed

demo-reset:
	uv run dqt demo reset

# ─── publish (PyPI via trusted publishing) ──────────────────────────
publish-rc:
	@echo "Tag the release with dqt-vX.Y.Z-rcN and push — CI handles the rest."

publish:
	@echo "Tag the release with dqt-vX.Y.Z and push — CI handles the rest."
