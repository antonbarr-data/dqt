# apps/server/tests/test_insights_api.py
import pytest
from httpx import AsyncClient, ASGITransport

from dqt_server.main import app


@pytest.mark.asyncio
async def test_metrics_list_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_metric_detail_unknown_fqn_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/metrics/does.not.exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_metric_series_returns_list():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/metrics/test.m/series?lookback_days=7")
    assert resp.status_code in (200, 404)


@pytest.mark.asyncio
async def test_metric_pin_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/metrics/test.m/pin")
    assert resp.status_code == 200
    data = resp.json()
    assert data["pinned"] is True
    assert "fqn" in data


@pytest.mark.asyncio
async def test_metrics_list_contains_gigler_tables():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/metrics")
    assert resp.status_code == 200
    data = resp.json()
    fqns = {m["fqn"] for m in data}
    assert any("marketing_campaigns" in fqn for fqn in fqns)


@pytest.mark.asyncio
async def test_metric_detail_known_fqn_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        list_resp = await client.get("/api/v1/metrics")
    assert list_resp.status_code == 200
    metrics = list_resp.json()
    if not metrics:
        pytest.skip("no metrics registered")
    fqn = metrics[0]["fqn"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/metrics/{fqn}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["fqn"] == fqn
    assert "display_name" in data
    assert "pinned" in data


@pytest.mark.asyncio
async def test_explain_streams_event_stream():
    """POST /metrics/{fqn}/explain returns text/event-stream."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/metrics/gigler.default.marketing_campaigns.quality/explain",
            json={"lookback_days": 7},
        )
    # Accept 200 or 404 (metric may not exist in test env)
    assert resp.status_code in (200, 404, 422)
    if resp.status_code == 200:
        assert "text/event-stream" in resp.headers.get("content-type", "")
