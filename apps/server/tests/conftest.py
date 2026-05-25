"""Server test configuration.

Pins all async tests to a session-scoped event loop so the SQLAlchemy
asyncpg connection pool is not recycled mid-session.
"""
import asyncio
import pytest
import pytest_asyncio


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def _session_loop():
    """Sentinel fixture to anchor the session-scoped loop."""
    yield


def pytest_collection_modifyitems(items):
    """Mark all async tests to use the session loop scope."""
    for item in items:
        if pytest_asyncio.is_async_test(item):
            item.add_marker(pytest.mark.asyncio(loop_scope="session"), append=False)
