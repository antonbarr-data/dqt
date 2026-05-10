# ClickHouse Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a ClickHouseAdapter that implements the WarehouseAdapter protocol so dqtlib can run DQ checks against ClickHouse warehouses.

**Architecture:** Mirror the existing PostgresAdapter exactly — SQLAlchemy engine via the `clickhouse+connect://` dialect (from `clickhouse-connect`), same 6-step health check, same method signatures. ClickHouse uses backtick identifier quoting and `system.tables`/`system.columns` instead of `information_schema`. Nullable columns are detected by checking if the type string starts with `Nullable(`.

**Tech Stack:** `clickhouse-connect>=0.7` (registers the SQLAlchemy dialect automatically), SQLAlchemy 2.0 (already a transitive dep), pandas (core dep), pytest + unittest.mock (no Docker needed for unit tests).

---

## File Map

| Action | Path |
|--------|------|
| Create | `packages/dqt/src/dqt/adapters/clickhouse/__init__.py` |
| Create | `packages/dqt/src/dqt/adapters/clickhouse/config.py` |
| Create | `packages/dqt/src/dqt/adapters/clickhouse/adapter.py` |
| Create | `packages/dqt/src/dqt/adapters/clickhouse/tests/__init__.py` |
| Create | `packages/dqt/src/dqt/adapters/clickhouse/tests/test_adapter.py` |
| Modify | `packages/dqt/src/dqt/adapters/__init__.py` |
| Modify | `packages/dqt/pyproject.toml` |

---

### Task 1: ClickHouseConfig + pyproject extra

**Files:**
- Create: `packages/dqt/src/dqt/adapters/clickhouse/config.py`
- Modify: `packages/dqt/pyproject.toml`

- [ ] **Step 1: Write the failing test**

Create `packages/dqt/src/dqt/adapters/clickhouse/tests/__init__.py` (empty) and `packages/dqt/src/dqt/adapters/clickhouse/tests/test_adapter.py`:

```python
from dqt.adapters.clickhouse.config import ClickHouseConfig


def test_config_defaults():
    cfg = ClickHouseConfig()
    assert cfg.host == "localhost"
    assert cfg.port == 8123
    assert cfg.database == "default"
    assert cfg.username == "default"
    assert cfg.password == ""
    assert cfg.secure is False


def test_config_conn_str():
    cfg = ClickHouseConfig(host="ch.example.com", port=8443, database="analytics",
                           username="alice", password="s3cr3t", secure=True)
    dsn = cfg.to_conn_str()
    assert dsn == "clickhouse+connect://alice:s3cr3t@ch.example.com:8443/analytics?secure=true"


def test_config_conn_str_insecure():
    cfg = ClickHouseConfig(host="localhost", port=8123, database="default",
                           username="default", password="")
    assert cfg.to_conn_str() == "clickhouse+connect://default:@localhost:8123/default"
```

- [ ] **Step 2: Run to confirm failure**

```
cd packages/dqt
uv run pytest src/dqt/adapters/clickhouse/tests/test_adapter.py -v
```

Expected: `ModuleNotFoundError: No module named 'dqt.adapters.clickhouse'`

- [ ] **Step 3: Create `packages/dqt/src/dqt/adapters/clickhouse/__init__.py`**

```python
from .adapter import ClickHouseAdapter
from .config import ClickHouseConfig

__all__ = ["ClickHouseAdapter", "ClickHouseConfig"]
```

- [ ] **Step 4: Create `packages/dqt/src/dqt/adapters/clickhouse/config.py`**

```python
from dataclasses import dataclass


@dataclass
class ClickHouseConfig:
    host: str = "localhost"
    port: int = 8123
    database: str = "default"
    username: str = "default"
    password: str = ""
    secure: bool = False

    def to_conn_str(self) -> str:
        base = f"clickhouse+connect://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        return f"{base}?secure=true" if self.secure else base
```

- [ ] **Step 5: Add clickhouse optional dep to `packages/dqt/pyproject.toml`**

In the `[project.optional-dependencies]` section, add after `files`:

```toml
clickhouse = ["clickhouse-connect>=0.7"]
```

- [ ] **Step 6: Run tests — expect failure on import of adapter**

```
cd packages/dqt
uv run pytest src/dqt/adapters/clickhouse/tests/test_adapter.py -v
```

Expected: `ImportError: cannot import name 'ClickHouseAdapter'` (config tests pass, adapter import fails)

- [ ] **Step 7: Commit**

```bash
git add packages/dqt/src/dqt/adapters/clickhouse/ packages/dqt/pyproject.toml
git commit -m "feat(clickhouse): config + pyproject extra"
```

---

### Task 2: ClickHouseAdapter implementation

**Files:**
- Create: `packages/dqt/src/dqt/adapters/clickhouse/adapter.py`

- [ ] **Step 1: Write the failing tests** (add to existing test file)

```python
from unittest.mock import MagicMock, patch, call
import pandas as pd
from dqt.adapters.clickhouse.adapter import ClickHouseAdapter
from dqt.adapters._protocol import AggExpr


def _make_adapter(conn_str="clickhouse+connect://default:@localhost:8123/default"):
    with patch("dqt.adapters.clickhouse.adapter.sa.create_engine") as mock_create:
        mock_engine = MagicMock()
        mock_create.return_value = mock_engine
        adapter = ClickHouseAdapter(conn_str)
        adapter._engine = mock_engine
    return adapter


def test_list_schemas():
    adapter = _make_adapter()
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchall.return_value = [("analytics",), ("raw",)]
    adapter._engine.connect.return_value.__enter__ = lambda s: mock_conn
    adapter._engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    schemas = adapter.list_schemas()
    assert schemas == ["analytics", "raw"]
    sql_called = mock_conn.execute.call_args[0][0].text
    assert "system.tables" in sql_called
    assert "NOT IN" in sql_called


def test_list_tables():
    adapter = _make_adapter()
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchall.return_value = [("events",), ("users",)]
    adapter._engine.connect.return_value.__enter__ = lambda s: mock_conn
    adapter._engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    tables = adapter.list_tables("analytics")
    assert tables == ["events", "users"]


def test_describe_columns_nullable():
    adapter = _make_adapter()
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchall.return_value = [
        ("id", "UInt64", 1),
        ("name", "Nullable(String)", 2),
    ]
    adapter._engine.connect.return_value.__enter__ = lambda s: mock_conn
    adapter._engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    cols = adapter.describe_columns("analytics", "users")
    assert cols[0].name == "id"
    assert cols[0].nullable is False
    assert cols[0].data_type == "UInt64"
    assert cols[1].name == "name"
    assert cols[1].nullable is True
    assert cols[1].data_type == "String"


def test_aggregate():
    adapter = _make_adapter()
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = (42, 0.05)
    adapter._engine.connect.return_value.__enter__ = lambda s: mock_conn
    adapter._engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    exprs = [AggExpr("cnt", "COUNT(*)"), AggExpr("frac", "AVG(x)")]
    result = adapter.aggregate("analytics", "events", exprs)
    assert result == {"cnt": 42, "frac": 0.05}
```

- [ ] **Step 2: Run to confirm failure**

```
cd packages/dqt
uv run pytest src/dqt/adapters/clickhouse/tests/test_adapter.py -v
```

Expected: `ImportError: cannot import name 'ClickHouseAdapter' from 'dqt.adapters.clickhouse.adapter'`

- [ ] **Step 3: Create `packages/dqt/src/dqt/adapters/clickhouse/adapter.py`**

```python
# ClickHouseAdapter: wraps clickhouse-connect via SQLAlchemy for warehouse operations.
# Sampling uses ORDER BY rand() LIMIT n (SAMPLE clause requires MergeTree+sample key).
from __future__ import annotations

import datetime
import time
from typing import Any

import pandas as pd
import sqlalchemy as sa

from dqt.adapters._protocol import (
    AggExpr,
    ColumnMeta,
    HealthCheckResult,
    HealthCheckStep,
)
from dqt.utils.logging import get_logger

_log = get_logger(__name__)

_SYSTEM_DBS = "('system', 'information_schema', 'INFORMATION_SCHEMA')"


class ClickHouseAdapter:
    def __init__(self, conn_str: str) -> None:
        self._conn_str = conn_str
        self._engine = sa.create_engine(conn_str, pool_pre_ping=True)

    def health_check(self) -> HealthCheckResult:
        steps: list[HealthCheckStep] = []
        steps.append(self._step_tcp())
        if steps[-1].status == "fail":
            for name in ("auth", "info_schema", "sample_select", "latency_probe", "clock_skew"):
                steps.append(HealthCheckStep(name=name, status="skip", latency_ms=0.0, detail="skipped"))
            return HealthCheckResult(steps=steps)
        steps.append(self._step_auth())
        steps.append(self._step_info_schema())
        steps.append(self._step_sample_select())
        steps.append(self._step_latency())
        steps.append(self._step_clock_skew())
        return HealthCheckResult(steps=steps)

    def _step_tcp(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            with self._engine.connect() as conn:
                conn.execute(sa.text("SELECT 1"))
            return HealthCheckStep("tcp_reach", "pass", (time.perf_counter() - t0) * 1000, "ok")
        except Exception as exc:
            return HealthCheckStep("tcp_reach", "fail", 0.0, str(exc))

    def _step_auth(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            with self._engine.connect() as conn:
                user = conn.execute(sa.text("SELECT currentUser()")).scalar()
            return HealthCheckStep("auth", "pass", (time.perf_counter() - t0) * 1000, f"user={user}")
        except Exception as exc:
            return HealthCheckStep("auth", "fail", 0.0, str(exc))

    def _step_info_schema(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            with self._engine.connect() as conn:
                conn.execute(sa.text(
                    f"SELECT COUNT(*) FROM system.tables WHERE database NOT IN {_SYSTEM_DBS}"
                )).scalar()
            return HealthCheckStep("info_schema", "pass", (time.perf_counter() - t0) * 1000, "readable")
        except Exception as exc:
            return HealthCheckStep("info_schema", "fail", 0.0, str(exc))

    def _step_sample_select(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            with self._engine.connect() as conn:
                conn.execute(sa.text(
                    f"SELECT name FROM system.tables WHERE database NOT IN {_SYSTEM_DBS} LIMIT 1"
                )).fetchone()
            return HealthCheckStep("sample_select", "pass", (time.perf_counter() - t0) * 1000, "ok")
        except Exception as exc:
            return HealthCheckStep("sample_select", "fail", 0.0, str(exc))

    def _step_latency(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            with self._engine.connect() as conn:
                conn.execute(sa.text("SELECT 1"))
            latency = (time.perf_counter() - t0) * 1000
            return HealthCheckStep("latency_probe", "pass", latency, f"{latency:.1f}ms")
        except Exception as exc:
            return HealthCheckStep("latency_probe", "fail", 0.0, str(exc))

    def _step_clock_skew(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            with self._engine.connect() as conn:
                ts = conn.execute(sa.text("SELECT toUnixTimestamp(now())")).scalar()
            local_ts = datetime.datetime.now(datetime.timezone.utc).timestamp()
            skew_s = abs(float(ts) - local_ts)
            status = "pass" if skew_s < 60 else "fail"
            return HealthCheckStep("clock_skew", status, (time.perf_counter() - t0) * 1000, f"skew={skew_s:.1f}s")
        except Exception as exc:
            return HealthCheckStep("clock_skew", "fail", 0.0, str(exc))

    def list_schemas(self) -> list[str]:
        with self._engine.connect() as conn:
            rows = conn.execute(sa.text(
                f"SELECT DISTINCT database FROM system.tables "
                f"WHERE database NOT IN {_SYSTEM_DBS} ORDER BY database"
            )).fetchall()
        return [r[0] for r in rows]

    def list_tables(self, schema: str) -> list[str]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                sa.text("SELECT name FROM system.tables WHERE database = :schema ORDER BY name"),
                {"schema": schema},
            ).fetchall()
        return [r[0] for r in rows]

    def describe_columns(self, schema: str, table: str) -> list[ColumnMeta]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                sa.text(
                    "SELECT name, type, position FROM system.columns "
                    "WHERE database = :schema AND table = :table ORDER BY position"
                ),
                {"schema": schema, "table": table},
            ).fetchall()
        result = []
        for r in rows:
            type_str: str = r[1]
            nullable = type_str.startswith("Nullable(")
            data_type = type_str[9:-1] if nullable else type_str
            result.append(ColumnMeta(name=r[0], data_type=data_type, nullable=nullable, position=r[2]))
        return result

    def sample(self, schema: str, table: str, n: int = 100_000) -> pd.DataFrame:
        query = sa.text(f"SELECT * FROM `{schema}`.`{table}` ORDER BY rand() LIMIT :n")
        with self._engine.connect() as conn:
            return pd.read_sql(query, conn, params={"n": n})

    def aggregate(self, schema: str, table: str, exprs: list[AggExpr]) -> dict[str, Any]:
        cols = ", ".join(f"{e.sql} AS {e.name}" for e in exprs)
        query = sa.text(f"SELECT {cols} FROM `{schema}`.`{table}`")
        with self._engine.connect() as conn:
            row = conn.execute(query).fetchone()
        return dict(zip([e.name for e in exprs], row))
```

- [ ] **Step 4: Run tests — should pass**

```
cd packages/dqt
uv run pytest src/dqt/adapters/clickhouse/tests/test_adapter.py -v
```

Expected: all 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add packages/dqt/src/dqt/adapters/clickhouse/
git commit -m "feat(clickhouse): ClickHouseAdapter implementation"
```

---

### Task 3: Export from adapters package + version bump

**Files:**
- Modify: `packages/dqt/src/dqt/adapters/__init__.py`
- Modify: `packages/dqt/pyproject.toml` (version bump to 0.1.4)

- [ ] **Step 1: Update `packages/dqt/src/dqt/adapters/__init__.py`**

```python
from .clickhouse import ClickHouseAdapter, ClickHouseConfig
from .postgres import PostgresAdapter, PostgresConfig

__all__ = [
    "ClickHouseAdapter",
    "ClickHouseConfig",
    "PostgresAdapter",
    "PostgresConfig",
]
```

- [ ] **Step 2: Bump version in `packages/dqt/pyproject.toml`**

Change:
```toml
version = "0.1.3"
```
To:
```toml
version = "0.1.4"
```

- [ ] **Step 3: Verify full test suite passes**

```
cd packages/dqt
uv run pytest src/ -v --ignore=src/dqt/adapters/clickhouse/tests/test_adapter.py
uv run pytest src/dqt/adapters/clickhouse/tests/test_adapter.py -v
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add packages/dqt/src/dqt/adapters/__init__.py packages/dqt/pyproject.toml
git commit -m "feat(clickhouse): export from adapters package, bump dqtlib to 0.1.4"
```

---

### Task 4: Health check tests

**Files:**
- Modify: `packages/dqt/src/dqt/adapters/clickhouse/tests/test_adapter.py`

- [ ] **Step 1: Add health check tests**

```python
def test_health_check_pass():
    adapter = _make_adapter()
    mock_conn = MagicMock()
    # All queries succeed
    mock_conn.execute.return_value.scalar.return_value = 1
    mock_conn.execute.return_value.fetchone.return_value = ("events",)
    adapter._engine.connect.return_value.__enter__ = lambda s: mock_conn
    adapter._engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    result = adapter.health_check()
    assert result.passed is True
    assert len(result.steps) == 6
    assert all(s.status == "pass" for s in result.steps)


def test_health_check_tcp_fail():
    adapter = _make_adapter()
    adapter._engine.connect.side_effect = Exception("Connection refused")

    result = adapter.health_check()
    assert result.passed is False
    assert result.steps[0].name == "tcp_reach"
    assert result.steps[0].status == "fail"
    assert all(s.status == "skip" for s in result.steps[1:])


def test_health_check_clock_skew_fail():
    import time as _time
    adapter = _make_adapter()
    mock_conn = MagicMock()
    # Return a timestamp 120 seconds in the past
    stale_ts = int(_time.time()) - 120
    mock_conn.execute.return_value.scalar.return_value = stale_ts
    mock_conn.execute.return_value.fetchone.return_value = ("t",)
    adapter._engine.connect.return_value.__enter__ = lambda s: mock_conn
    adapter._engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    result = adapter.health_check()
    clock_step = next(s for s in result.steps if s.name == "clock_skew")
    assert clock_step.status == "fail"
```

- [ ] **Step 2: Run**

```
cd packages/dqt
uv run pytest src/dqt/adapters/clickhouse/tests/test_adapter.py -v
```

Expected: all 9 tests pass.

- [ ] **Step 3: Commit**

```bash
git add packages/dqt/src/dqt/adapters/clickhouse/tests/
git commit -m "test(clickhouse): health check unit tests"
```
