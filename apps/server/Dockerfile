FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY . .
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python --no-cache .

CMD sh -c '/app/.venv/bin/uvicorn dqt_server.main:app --host 0.0.0.0 --port $PORT'
