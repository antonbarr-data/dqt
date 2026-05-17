# apps/server/tests/test_suggest_api.py
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

from dqt_server.db.engine import get_db
from dqt_server.main import app


def _make_db_stub(dataset_return=None):
    """Return an async generator that yields a mock AsyncSession."""
    db = AsyncMock()
    db.get = AsyncMock(return_value=dataset_return)

    async def _override():
        yield db

    return _override


@pytest.mark.asyncio
async def test_suggest_endpoint_unknown_dataset_returns_404():
    """When db.get returns None the endpoint must 404."""
    app.dependency_overrides[get_db] = _make_db_stub(dataset_return=None)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/datasets/nonexistent_table_xyz/columns/id/suggest"
            )
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_suggest_endpoint_response_shape():
    """When a dataset row exists the endpoint returns a list with the expected keys."""
    fake_dataset = MagicMock()
    app.dependency_overrides[get_db] = _make_db_stub(dataset_return=fake_dataset)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/datasets/gigler_transactions/columns/price_id/suggest"
            )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            item = data[0]
            assert "detector_slug" in item
            assert "rationale" in item
            assert "confidence" in item
            assert isinstance(item["confidence"], float)
    finally:
        app.dependency_overrides.pop(get_db, None)
