import pytest
from httpx import AsyncClient, ASGITransport
from dqt_server.main import app

@pytest.mark.asyncio
async def test_ask_returns_answer_or_disambiguation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/ask", json={"question": "Why is quality down this week?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] in ("answer", "disambiguation")

@pytest.mark.asyncio
async def test_ask_disambiguation_has_options():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/ask", json={"question": "Why is xyz123notexist down?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] == "disambiguation"
    assert "options" in body

@pytest.mark.asyncio
async def test_ask_clarify():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/ask/clarify", json={
            "question": "Why is quality down?",
            "chosen_fqn": "gigler.default.fct_orders.quality",
        })
    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] in ("answer", "disambiguation")
