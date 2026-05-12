# packages/dqt/src/dqt/dashboard/__init__.py
# Optional module — requires dqtlib[dashboard] (fastapi, uvicorn, jinja2).
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dqt.store._protocol import ResultsStore


def create_app(store: "ResultsStore | None" = None, lineage_graph=None):
    """Return a FastAPI application serving the local dqt dashboard.

    Requires: pip install 'dqtlib[dashboard]'

    Example
    -------
    >>> from dqt.dashboard import create_app
    >>> app = create_app()
    """
    try:
        from dqt.dashboard.app import build_app
    except ImportError as exc:
        raise ImportError(
            "dqt dashboard requires fastapi, uvicorn, and jinja2. "
            "Install with: pip install 'dqtlib[dashboard]'"
        ) from exc
    if store is None:
        from dqt.store.memory import MemoryStore
        store = MemoryStore()
    return build_app(store, lineage_graph=lineage_graph)


__all__ = ["create_app"]
