import pytest
from httpx import AsyncClient, ASGITransport
from dqt_server.main import app

@pytest.mark.asyncio
async def test_feed_today_returns_list():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/feed/today")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_feed_today_limit_param():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/feed/today?limit=2")
    assert resp.status_code == 200
    assert len(resp.json()) <= 2

@pytest.mark.asyncio
async def test_feed_weekly_returns_list():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/feed/weekly")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

@pytest.mark.asyncio
async def test_mark_reviewed():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/feed/items/nonexistent-id/reviewed")
    assert resp.status_code in (200, 404)
