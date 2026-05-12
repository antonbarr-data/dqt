# packages/dqt/tests/store/test_postgres_store.py
"""Tests for PostgresStore -- mocked psycopg2, no real database required."""
import importlib
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from dqt.algorithms._base import Verdict
from dqt.store._protocol import Incident, RunResult
from dqt.store.proof import ProofBundle


def _make_run(**kwargs):
    now = datetime.now(timezone.utc)
    defaults = dict(
        run_id=uuid4(), check_id=uuid4(), detector_slug="ks_pvalue",
        detector_version="1", started_at=now, finished_at=now,
        verdict=Verdict.pass_, score=0.1, plain_english="ok", details={},
    )
    defaults.update(kwargs)
    return RunResult(**defaults)


def test_postgres_store_import_error():
    """Without psycopg2, PostgresStore raises ImportError with install hint."""
    original = sys.modules.get("psycopg2")
    sys.modules["psycopg2"] = None  # type: ignore
    try:
        import dqt.store.postgres as pg_mod
        importlib.reload(pg_mod)
        with pytest.raises(ImportError, match="psycopg2"):
            pg_mod.PostgresStore("postgresql://fake/fake")
    finally:
        if original is not None:
            sys.modules["psycopg2"] = original
        else:
            sys.modules.pop("psycopg2", None)
        importlib.reload(pg_mod)


def test_postgres_store_initializes_with_mock():
    """PostgresStore initializes and creates schema when psycopg2 is mocked."""
    fake_cursor = MagicMock()
    fake_cursor.__enter__ = lambda s: s
    fake_cursor.__exit__ = MagicMock(return_value=False)
    fake_conn = MagicMock()
    fake_conn.cursor.return_value = fake_cursor
    with patch("psycopg2.connect", return_value=fake_conn):
        with patch("psycopg2.extras.RealDictCursor"):
            from dqt.store.postgres import PostgresStore
            store = PostgresStore("postgresql://fake/fake")
            assert store is not None
            fake_conn.commit.assert_called()
