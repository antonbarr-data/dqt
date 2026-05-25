import pytest
from httpx import AsyncClient, ASGITransport

from dqt_server.main import app


@pytest.mark.asyncio
async def test_evaluate_expression_missing_source():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/metrics/evaluate-expression", json={
            "dataset": "nonexistent_table",
            "source_id": "nonexistent_source",
            "expr_sql": "SUM(amount_usd)",
        })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_evaluate_metric_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/metrics/does.not.exist.fake_metric/evaluate")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
