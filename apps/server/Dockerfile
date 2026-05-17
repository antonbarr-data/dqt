FROM python:3.12-slim

WORKDIR /app

# Build context = apps/server/ (Railway root directory)
# pip ignores [tool.uv.sources]; dqtlib>=0.9.1 resolves to PyPI v1.3.0
COPY . .
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "dqt_server.main:app", "--host", "0.0.0.0", "--port", "8000"]
