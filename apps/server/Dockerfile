FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

ENV PATH="/app/.venv/bin:$PATH"

COPY . .
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python --no-cache .

EXPOSE 8000
CMD ["uvicorn", "dqt_server.main:app", "--host", "0.0.0.0", "--port", "8000"]
