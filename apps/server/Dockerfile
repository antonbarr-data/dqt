FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

ENV PATH="/app/.venv/bin:$PATH"

# Build context = repo root; copy only what the server needs
COPY packages/dqt packages/dqt
COPY apps/server apps/server
COPY pyproject.toml uv.lock ./

# Install via workspace sync so dqtlib comes from packages/dqt, not PyPI
RUN uv sync --frozen --package dqt-server

EXPOSE 8000
CMD ["uvicorn", "dqt_server.main:app", "--host", "0.0.0.0", "--port", "8000"]
