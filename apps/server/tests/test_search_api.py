import pytest
from httpx import AsyncClient, ASGITransport
from dqt_server.main import app

@pytest.mark.asyncio
async def test_search_returns_list():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/metrics/search?q=quality")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

@pytest.mark.asyncio
async def test_search_empty_query_returns_all():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/metrics/search?q=")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

@pytest.mark.asyncio
async def test_search_limit_param():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/metrics/search?q=&limit=2")
    assert resp.status_code == 200
    assert len(resp.json()) <= 2
