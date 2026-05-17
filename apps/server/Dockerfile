FROM python:3.12-slim

WORKDIR /app

# Build context = repo root
COPY packages/dqt packages/dqt
COPY apps/server apps/server

# pip ignores [tool.uv.sources]; installs dqtlib from local source,
# server deps from PyPI — no uv.lock required.
RUN pip install --no-cache-dir ./packages/dqt && \
    pip install --no-cache-dir ./apps/server

EXPOSE 8000
CMD ["uvicorn", "dqt_server.main:app", "--host", "0.0.0.0", "--port", "8000"]
