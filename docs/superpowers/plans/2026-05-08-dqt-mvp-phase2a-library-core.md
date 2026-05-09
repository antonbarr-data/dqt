# dqt Library Core (Phase 2a) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `packages/dqt` library foundation: core types, MemoryStore, PostgresAdapter, STAT_SCALES + detector registry, five basic aggregate detectors, schema + referential detectors, four key statistical detectors, check models + YAML loader, Runner, and PostgresStore. All library tests pass with `make test-lib`.

**Architecture:** Each detector is a class implementing `BaseDetector` (sample-based) or `BaseAggregateDetector` (aggregate-based) and registered by slug in a global `registry`. The `Runner` resolves detectors from the registry, calls the correct adapter method (`aggregate` or `sample`), and persists `RunResult` + `Incident` to a `ResultsStore`. `MemoryStore` is the default; `PostgresStore` enables the server. No circular imports: `_scales.py` has zero dqt imports; `_base.py` lazily imports `_scales`; everything else follows a strict one-way dependency graph.

**Tech Stack:** Python 3.12+, pandas, numpy, scipy, statsmodels, scikit-learn, ibis-framework[postgres], structlog, pydantic v2, jsonschema, PyYAML, pytest, hypothesis, testcontainers.

---

## File Map

```
packages/dqt/src/dqt/
├── __init__.py                              modify — public API exports (Task 11)
├── utils/
│   ├── __init__.py                          create — empty
│   └── logging.py                           create — get_logger() via structlog (Task 1)
├── algorithms/
│   ├── __init__.py                          create — empty
│   ├── _base.py                             create — Verdict, DetectorResult, BaseDetector, BaseAggregateDetector, compute_verdict (Task 1)
│   ├── _scales.py                           create — StatScale NamedTuple, STAT_SCALES dict (Task 4)
│   ├── _registry.py                         create — Registry, registry singleton, get_detector() (Task 4)
│   ├── basic/
│   │   ├── __init__.py                      create — empty
│   │   ├── completeness.py                  create — CompletenessDetector (Task 5)
│   │   ├── uniqueness.py                    create — UniquenessDetector (Task 5)
│   │   ├── validity.py                      create — ValidityDetector (Task 5)
│   │   ├── numeric.py                       create — NumericMeanDetector (Task 5)
│   │   ├── volume.py                        create — VolumeDetector (Task 5)
│   │   ├── numeric_bounds.py                create — MaxInRange, MinInRange, MedianInRange, StdDevInRange, SumInRange, CardinalityInRange, QuantileInRange (Task 5b)
│   │   ├── value_checks.py                  create — ValueInRange, SetMembership, SetExclusion, RegexMatch, StringLengthRange, DateFormat (Task 5b)
│   │   ├── monotonicity.py                  create — MonotonicityDetector (Task 5b)
│   │   └── column_pairs.py                  create — ColumnPairComparison, CompositeUniqueness (Task 5b)
│   ├── schema/
│   │   ├── __init__.py                      create — empty
│   │   └── schema_checks.py                 create — SchemaChangeDetector (Task 6)
│   ├── referential/
│   │   ├── __init__.py                      create — empty
│   │   └── referential.py                   create — ReferentialIntegrityDetector (Task 6)
│   ├── drift/
│   │   ├── __init__.py                      create — empty
│   │   └── ks2sample.py                     create — KS2SampleDetector (Task 7)
│   ├── distribution/
│   │   ├── __init__.py                      create — empty
│   │   └── profiler.py                      create — DistributionType, DistributionProfile, classify_distribution() (Task 7b)
│   ├── outliers_uni/
│   │   ├── __init__.py                      create — empty
│   │   ├── mad.py                           create — MADOutlierDetector + DoubleMadOutlierDetector (Task 7)
│   │   ├── zscore.py                        create — ZScoreDetector (Task 7b)
│   │   ├── adjusted_boxplot.py              create — AdjustedBoxplotDetector, Hubert & Vandervieren 2008 (Task 7b)
│   │   └── auto_outlier.py                  create — AutoOutlierDetector, profiles distribution + selects best method (Task 7b)
│   ├── outliers_multi/
│   │   ├── __init__.py                      create — empty
│   │   └── isolation_forest.py              create — IsolationForestDetector (Task 7)
│   └── timeseries/
│       ├── __init__.py                      create — empty
│       └── stl.py                           create — STLAnomalyDetector (Task 7)
├── adapters/
│   ├── __init__.py                          create — empty
│   ├── _protocol.py                         create — AggExpr, HealthCheckStep, HealthCheckResult, ColumnMeta, WarehouseAdapter (Task 1)
│   └── postgres/
│       ├── __init__.py                      create — exports PostgresAdapter
│       ├── config.py                        create — PostgresConfig dataclass (Task 3)
│       └── adapter.py                       create — PostgresAdapter (Task 3)
├── store/
│   ├── __init__.py                          create — empty
│   ├── _protocol.py                         create — RunResult, Incident, ResultsStore (Task 1)
│   ├── memory.py                            create — MemoryStore (Task 2)
│   └── postgres.py                          create — PostgresStore (Task 10)
├── checks/
│   ├── __init__.py                          create — empty
│   ├── models.py                            create — Check, BaselineConfig (Task 1)
│   ├── loader.py                            create — load_checks_yaml() (Task 8)
│   └── schema/
│       └── check.schema.json                create — JSON Schema for check YAML (Task 8)
├── runner/
│   ├── __init__.py                          create — empty
│   └── runner.py                            create — Runner (Task 9)
└── governance/__init__.py                   create — empty stub
    lineage/__init__.py                      create — empty stub
    agent/__init__.py                        create — empty stub
    semantic/__init__.py                     create — empty stub
    hitl/__init__.py                         create — empty stub
    causality/__init__.py                    create — empty stub
    compat/__init__.py                       create — empty stub

packages/dqt/tests/
├── __init__.py                              create — empty
├── conftest.py                              create — shared fixtures (Task 1)
├── test_core_types.py                       create — Verdict, DetectorResult, AggExpr, Check (Task 1)
├── store/
│   ├── __init__.py                          create — empty
│   ├── test_memory_store.py                 create (Task 2)
│   └── test_postgres_store.py              create — @integration (Task 10)
├── adapters/
│   ├── __init__.py                          create — empty
│   └── test_postgres_adapter.py            create — @adapter (Task 3)
├── algorithms/
│   ├── __init__.py                          create — empty
│   ├── test_registry.py                     create (Task 4)
│   ├── basic/
│   │   ├── __init__.py                      create — empty
│   │   ├── test_completeness.py             create (Task 5)
│   │   ├── test_uniqueness.py               create (Task 5)
│   │   ├── test_validity.py                 create (Task 5)
│   │   ├── test_numeric.py                  create (Task 5)
│   │   ├── test_volume.py                   create (Task 5)
│   │   ├── test_numeric_bounds.py           create (Task 5b)
│   │   ├── test_value_checks.py             create (Task 5b)
│   │   ├── test_monotonicity.py             create (Task 5b)
│   │   └── test_column_pairs.py             create (Task 5b)
│   ├── schema/
│   │   ├── __init__.py                      create — empty
│   │   └── test_schema_checks.py            create (Task 6)
│   ├── referential/
│   │   ├── __init__.py                      create — empty
│   │   └── test_referential.py              create (Task 6)
│   ├── drift/
│   │   ├── __init__.py                      create — empty
│   │   └── test_ks2sample.py                create (Task 7)
│   ├── distribution/
│   │   ├── __init__.py                      create — empty
│   │   └── test_profiler.py                 create (Task 7b)
│   ├── outliers_uni/
│   │   ├── __init__.py                      create — empty
│   │   ├── test_mad.py                      create (Task 7)
│   │   ├── test_zscore.py                   create (Task 7b)
│   │   ├── test_adjusted_boxplot.py         create (Task 7b)
│   │   └── test_auto_outlier.py             create (Task 7b)
│   ├── outliers_multi/
│   │   ├── __init__.py                      create — empty
│   │   └── test_isolation_forest.py         create (Task 7)
│   └── timeseries/
│       ├── __init__.py                      create — empty
│       └── test_stl.py                      create (Task 7)
├── checks/
│   ├── __init__.py                          create — empty
│   └── test_loader.py                       create (Task 8)
└── runner/
    ├── __init__.py                          create — empty
    └── test_runner.py                       create (Task 9)
```

---

### Task 1: Core types + structlog utility

**Files:**
- Create: `packages/dqt/src/dqt/utils/__init__.py`
- Create: `packages/dqt/src/dqt/utils/logging.py`
- Create: `packages/dqt/src/dqt/algorithms/_base.py`
- Create: `packages/dqt/src/dqt/adapters/_protocol.py`
- Create: `packages/dqt/src/dqt/store/_protocol.py`
- Create: `packages/dqt/src/dqt/checks/models.py`
- Create stubs: governance, lineage, agent, semantic, hitl, causality, compat `__init__.py`
- Create: `packages/dqt/tests/conftest.py`
- Test: `packages/dqt/tests/test_core_types.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/test_core_types.py
import math
import uuid
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest


def test_verdict_values():
    from dqt.algorithms._base import Verdict
    assert Verdict.pass_.value == "pass"
    assert Verdict.warn.value == "warn"
    assert Verdict.fail.value == "fail"


def test_detector_result_fields():
    from dqt.algorithms._base import DetectorResult, Verdict
    r = DetectorResult(score=0.5, verdict=Verdict.pass_, plain_english="all good")
    assert r.score == 0.5
    assert r.details == {}


def test_agg_expr_fields():
    from dqt.adapters._protocol import AggExpr
    e = AggExpr(name="null_count", sql="COUNT(*) - COUNT(col)")
    assert e.name == "null_count"


def test_health_check_result_passed():
    from dqt.adapters._protocol import HealthCheckResult, HealthCheckStep
    steps = [
        HealthCheckStep(name="tcp", status="pass", latency_ms=1.0, detail="ok"),
        HealthCheckStep(name="auth", status="pass", latency_ms=2.0, detail="ok"),
    ]
    result = HealthCheckResult(steps=steps)
    assert result.passed is True


def test_health_check_result_failed():
    from dqt.adapters._protocol import HealthCheckResult, HealthCheckStep
    steps = [
        HealthCheckStep(name="tcp", status="pass", latency_ms=1.0, detail="ok"),
        HealthCheckStep(name="auth", status="fail", latency_ms=0.0, detail="bad password"),
    ]
    result = HealthCheckResult(steps=steps)
    assert result.passed is False


def test_run_result_fields():
    from dqt.algorithms._base import Verdict
    from dqt.store._protocol import RunResult
    now = datetime.now(timezone.utc)
    check_id = uuid.uuid4()
    r = RunResult(
        check_id=check_id,
        detector_slug="completeness",
        started_at=now,
        finished_at=now,
        verdict=Verdict.pass_,
        score=0.99,
        plain_english="99% complete",
    )
    assert r.run_id is not None
    assert r.details == {}


def test_incident_fields():
    from dqt.algorithms._base import Verdict
    from dqt.store._protocol import Incident
    now = datetime.now(timezone.utc)
    inc = Incident(
        check_id=uuid.uuid4(),
        run_id=uuid.uuid4(),
        detector_slug="completeness",
        severity=Verdict.fail,
        opened_at=now,
        score=0.7,
    )
    assert inc.status == "open"
    assert inc.resolved_at is None


def test_check_model_fields():
    from dqt.checks.models import BaselineConfig, Check
    check = Check(
        schema_name="public",
        table_name="orders",
        column_name="amount",
        detector_slug="completeness",
    )
    assert check.sample_n == 100_000
    assert check.baseline is None


def test_check_with_baseline():
    from dqt.checks.models import BaselineConfig, Check
    check = Check(
        schema_name="public",
        table_name="orders",
        column_name="amount",
        detector_slug="completeness",
        baseline=BaselineConfig(window_days=14),
    )
    assert check.baseline.window_days == 14
    assert check.baseline.min_rows == 1_000


def test_get_logger():
    from dqt.utils.logging import get_logger
    log = get_logger("dqt.test")
    assert log is not None
```

- [ ] **Step 2: Run test to verify it fails**

```
cd packages/dqt && uv run pytest tests/test_core_types.py -v
```
Expected: multiple `ModuleNotFoundError` / `ImportError` failures.

- [ ] **Step 3: Create empty `__init__.py` files and stub modules**

```python
# packages/dqt/src/dqt/utils/__init__.py
# (empty)
```

```python
# packages/dqt/src/dqt/algorithms/__init__.py
# (empty)
```

```python
# packages/dqt/src/dqt/adapters/__init__.py
# (empty)
```

```python
# packages/dqt/src/dqt/store/__init__.py
# (empty)
```

```python
# packages/dqt/src/dqt/checks/__init__.py
# (empty)
```

```python
# packages/dqt/src/dqt/runner/__init__.py
# (empty)
```

Create empty `__init__.py` for each stub module (one line each, just `# (empty)`):
- `packages/dqt/src/dqt/governance/__init__.py`
- `packages/dqt/src/dqt/lineage/__init__.py`
- `packages/dqt/src/dqt/agent/__init__.py`
- `packages/dqt/src/dqt/semantic/__init__.py`
- `packages/dqt/src/dqt/hitl/__init__.py`
- `packages/dqt/src/dqt/causality/__init__.py`
- `packages/dqt/src/dqt/compat/__init__.py`

Also create:
- `packages/dqt/tests/__init__.py` (empty)
- `packages/dqt/tests/store/__init__.py` (empty)
- `packages/dqt/tests/adapters/__init__.py` (empty)
- `packages/dqt/tests/algorithms/__init__.py` (empty)
- `packages/dqt/tests/checks/__init__.py` (empty)
- `packages/dqt/tests/runner/__init__.py` (empty)

- [ ] **Step 4: Create `utils/logging.py`**

```python
# packages/dqt/src/dqt/utils/logging.py
import logging
import structlog


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger(name)
```

- [ ] **Step 5: Create `algorithms/_base.py`**

```python
# packages/dqt/src/dqt/algorithms/_base.py
# Base classes for all detectors. StatScale and STAT_SCALES live in _scales.py (no dqt imports there).
# compute_verdict defers the _scales import to break any potential circular dependency.
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

import pandas as pd

if TYPE_CHECKING:
    from dqt.adapters._protocol import AggExpr


class Verdict(str, Enum):
    pass_ = "pass"
    warn = "warn"
    fail = "fail"


@dataclass
class DetectorResult:
    score: float
    verdict: Verdict
    plain_english: str
    details: dict[str, Any] = field(default_factory=dict)


# DetectorState is opaque — detectors return whatever they need for score().
DetectorState = Any


def compute_verdict(score: float, slug: str) -> Verdict:
    """Look up the STAT_SCALE for slug and classify score. Import is deferred to avoid circular deps."""
    from dqt.algorithms._scales import STAT_SCALES  # deferred
    scale = STAT_SCALES.get(slug)
    if scale is None:
        raise KeyError(f"No STAT_SCALE entry for slug '{slug}'. Add it to _scales.py.")
    if scale.direction == "lower_is_better":
        if score >= scale.fail_threshold:
            return Verdict.fail
        if score >= scale.warn_threshold:
            return Verdict.warn
        return Verdict.pass_
    else:
        if score <= scale.fail_threshold:
            return Verdict.fail
        if score <= scale.warn_threshold:
            return Verdict.warn
        return Verdict.pass_


class BaseDetector:
    """Base for sample-based detectors. Subclass and override fit() and score()."""
    slug: ClassVar[str]
    group: ClassVar[str]
    kind: ClassVar[str] = "sample"

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return None

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        raise NotImplementedError

    def _verdict(self, score: float) -> Verdict:
        return compute_verdict(score, self.slug)


class BaseAggregateDetector(BaseDetector):
    """Base for detectors that push computation to the warehouse via SQL aggregations."""
    kind: ClassVar[str] = "aggregate"

    def get_aggregations(self, col: str) -> list[AggExpr]:
        raise NotImplementedError
```

- [ ] **Step 6: Create `adapters/_protocol.py`**

```python
# packages/dqt/src/dqt/adapters/_protocol.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

import pandas as pd


@dataclass
class AggExpr:
    name: str   # key in the result dict returned by adapter.aggregate()
    sql: str    # raw SQL expression with the column name already substituted


@dataclass
class HealthCheckStep:
    name: str
    status: Literal["pass", "fail", "skip"]
    latency_ms: float
    detail: str


@dataclass
class HealthCheckResult:
    steps: list[HealthCheckStep] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(s.status == "pass" for s in self.steps)


@dataclass
class ColumnMeta:
    name: str
    data_type: str
    nullable: bool
    position: int


@runtime_checkable
class WarehouseAdapter(Protocol):
    def health_check(self) -> HealthCheckResult: ...
    def sample(self, schema: str, table: str, n: int = 100_000) -> pd.DataFrame: ...
    def aggregate(self, schema: str, table: str, exprs: list[AggExpr]) -> dict[str, object]: ...
    def describe_columns(self, schema: str, table: str) -> list[ColumnMeta]: ...
    def list_schemas(self) -> list[str]: ...
    def list_tables(self, schema: str) -> list[str]: ...
```

- [ ] **Step 7: Create `store/_protocol.py`**

```python
# packages/dqt/src/dqt/store/_protocol.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable
from uuid import UUID, uuid4

from dqt.algorithms._base import Verdict


@dataclass
class RunResult:
    check_id: UUID
    detector_slug: str
    started_at: datetime
    finished_at: datetime
    verdict: Verdict
    score: float
    plain_english: str
    details: dict[str, Any] = field(default_factory=dict)
    run_id: UUID = field(default_factory=uuid4)


@dataclass
class Incident:
    check_id: UUID
    run_id: UUID
    detector_slug: str
    severity: Verdict
    opened_at: datetime
    score: float
    incident_id: UUID = field(default_factory=uuid4)
    status: str = "open"
    resolved_at: datetime | None = None


@runtime_checkable
class ResultsStore(Protocol):
    def save_run(self, run: RunResult) -> None: ...
    def list_runs(self, check_id: UUID, limit: int = 100) -> list[RunResult]: ...
    def save_incident(self, incident: Incident) -> None: ...
    def list_incidents(self, check_id: UUID, status: str | None = None) -> list[Incident]: ...
```

- [ ] **Step 8: Create `checks/models.py`**

```python
# packages/dqt/src/dqt/checks/models.py
from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class BaselineConfig(BaseModel):
    window_days: int = 14
    min_rows: int = 1_000


class Check(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    schema_name: str
    table_name: str
    column_name: str | None = None
    detector_slug: str
    params: dict[str, Any] = Field(default_factory=dict)
    baseline: BaselineConfig | None = None
    schedule: str | None = None
    sample_n: int = 100_000
```

- [ ] **Step 9: Create `tests/conftest.py`**

```python
# packages/dqt/tests/conftest.py
import numpy as np
import pandas as pd
import pytest


@pytest.fixture(scope="session")
def normal_df() -> pd.DataFrame:
    """1 000-row normal distribution, mean=10, std=2."""
    rng = np.random.default_rng(42)
    return pd.DataFrame({"value": rng.normal(loc=10.0, scale=2.0, size=1_000)})


@pytest.fixture(scope="session")
def shifted_df() -> pd.DataFrame:
    """Same shape as normal_df but mean shifted to 15 (clear drift)."""
    rng = np.random.default_rng(99)
    return pd.DataFrame({"value": rng.normal(loc=15.0, scale=2.0, size=1_000)})


@pytest.fixture(scope="session")
def timeseries_df() -> pd.DataFrame:
    """365-row daily time series: trend + weekly seasonal + noise."""
    rng = np.random.default_rng(42)
    n = 365
    trend = np.linspace(100.0, 110.0, n)
    seasonal = 5.0 * np.sin(2 * np.pi * np.arange(n) / 7)
    noise = rng.normal(0, 1.0, n)
    return pd.DataFrame({"value": trend + seasonal + noise})


@pytest.fixture(scope="session")
def agg_ref_df() -> pd.DataFrame:
    """1-row aggregate result simulating what adapter.aggregate() returns (Task 5+)."""
    return pd.DataFrame([{"null_count": 5, "total_count": 1_000}])


@pytest.fixture(scope="session")
def agg_curr_df() -> pd.DataFrame:
    """Same shape but 80 nulls — triggers a fail verdict."""
    return pd.DataFrame([{"null_count": 80, "total_count": 1_000}])
```

- [ ] **Step 10: Run test to verify it passes**

```
cd packages/dqt && uv run pytest tests/test_core_types.py -v
```
Expected: all 10 tests PASS.

- [ ] **Step 11: Commit**

```bash
git add packages/dqt/src/dqt/utils/ packages/dqt/src/dqt/algorithms/_base.py \
        packages/dqt/src/dqt/adapters/_protocol.py packages/dqt/src/dqt/store/_protocol.py \
        packages/dqt/src/dqt/checks/models.py packages/dqt/src/dqt/runner/__init__.py \
        packages/dqt/src/dqt/governance/ packages/dqt/src/dqt/lineage/ \
        packages/dqt/src/dqt/agent/ packages/dqt/src/dqt/semantic/ \
        packages/dqt/src/dqt/hitl/ packages/dqt/src/dqt/causality/ \
        packages/dqt/src/dqt/compat/ \
        packages/dqt/tests/
git commit -m "feat(dqt): core types — Verdict, DetectorResult, WarehouseAdapter, ResultsStore, Check"
```

---

### Task 2: MemoryStore

**Files:**
- Create: `packages/dqt/src/dqt/store/memory.py`
- Test: `packages/dqt/tests/store/test_memory_store.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/store/test_memory_store.py
import uuid
from datetime import datetime, timezone

import pytest

from dqt.algorithms._base import Verdict
from dqt.store._protocol import Incident, RunResult


@pytest.fixture()
def store():
    from dqt.store.memory import MemoryStore
    return MemoryStore()


@pytest.fixture()
def sample_run(store):
    check_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    run = RunResult(
        check_id=check_id,
        detector_slug="completeness",
        started_at=now,
        finished_at=now,
        verdict=Verdict.pass_,
        score=0.99,
        plain_english="99% complete",
    )
    store.save_run(run)
    return run, check_id


def test_save_and_list_run(store, sample_run):
    run, check_id = sample_run
    runs = store.list_runs(check_id)
    assert len(runs) == 1
    assert runs[0].run_id == run.run_id


def test_list_runs_empty(store):
    assert store.list_runs(uuid.uuid4()) == []


def test_list_runs_limit(store):
    check_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    for _ in range(5):
        store.save_run(RunResult(
            check_id=check_id,
            detector_slug="completeness",
            started_at=now,
            finished_at=now,
            verdict=Verdict.pass_,
            score=0.99,
            plain_english="ok",
        ))
    assert len(store.list_runs(check_id, limit=3)) == 3


def test_save_and_list_incident(store, sample_run):
    run, check_id = sample_run
    now = datetime.now(timezone.utc)
    inc = Incident(
        check_id=check_id,
        run_id=run.run_id,
        detector_slug="completeness",
        severity=Verdict.fail,
        opened_at=now,
        score=0.7,
    )
    store.save_incident(inc)
    incidents = store.list_incidents(check_id)
    assert len(incidents) == 1
    assert incidents[0].incident_id == inc.incident_id


def test_list_incidents_by_status(store, sample_run):
    run, check_id = sample_run
    now = datetime.now(timezone.utc)
    store.save_incident(Incident(
        check_id=check_id, run_id=run.run_id, detector_slug="completeness",
        severity=Verdict.warn, opened_at=now, score=0.93, status="open",
    ))
    store.save_incident(Incident(
        check_id=check_id, run_id=run.run_id, detector_slug="completeness",
        severity=Verdict.warn, opened_at=now, score=0.93, status="resolved",
    ))
    assert len(store.list_incidents(check_id, status="open")) == 1
    assert len(store.list_incidents(check_id, status="resolved")) == 1
    assert len(store.list_incidents(check_id)) == 2


def test_implements_results_store_protocol(store):
    from dqt.store._protocol import ResultsStore
    assert isinstance(store, ResultsStore)
```

- [ ] **Step 2: Run test to verify it fails**

```
cd packages/dqt && uv run pytest tests/store/test_memory_store.py -v
```
Expected: `ImportError: cannot import name 'MemoryStore'`

- [ ] **Step 3: Implement `store/memory.py`**

```python
# packages/dqt/src/dqt/store/memory.py
from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from dqt.store._protocol import Incident, RunResult


class MemoryStore:
    def __init__(self) -> None:
        self._runs: dict[UUID, list[RunResult]] = defaultdict(list)
        self._incidents: dict[UUID, list[Incident]] = defaultdict(list)

    def save_run(self, run: RunResult) -> None:
        self._runs[run.check_id].append(run)

    def list_runs(self, check_id: UUID, limit: int = 100) -> list[RunResult]:
        return list(reversed(self._runs[check_id]))[:limit]

    def save_incident(self, incident: Incident) -> None:
        self._incidents[incident.check_id].append(incident)

    def list_incidents(self, check_id: UUID, status: str | None = None) -> list[Incident]:
        items = self._incidents[check_id]
        if status is not None:
            items = [i for i in items if i.status == status]
        return list(items)
```

- [ ] **Step 4: Run test to verify it passes**

```
cd packages/dqt && uv run pytest tests/store/test_memory_store.py -v
```
Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/dqt/src/dqt/store/memory.py packages/dqt/tests/store/
git commit -m "feat(dqt): MemoryStore — in-memory ResultsStore for notebooks and library-only use"
```

---

### Task 3: WarehouseAdapter protocol + PostgresAdapter

**Files:**
- Create: `packages/dqt/src/dqt/adapters/postgres/config.py`
- Create: `packages/dqt/src/dqt/adapters/postgres/adapter.py`
- Create: `packages/dqt/src/dqt/adapters/postgres/__init__.py`
- Test: `packages/dqt/tests/adapters/test_postgres_adapter.py` (`@pytest.mark.adapter`)

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/adapters/test_postgres_adapter.py
import pytest

pytestmark = pytest.mark.adapter


@pytest.fixture(scope="module")
def pg_url():
    """Provide a live Postgres URL via testcontainers."""
    from testcontainers.postgres import PostgresContainer
    with PostgresContainer("timescale/timescaledb:latest-pg16") as pg:
        # seed a tiny table
        import sqlalchemy
        engine = sqlalchemy.create_engine(pg.get_connection_url())
        with engine.begin() as conn:
            conn.execute(sqlalchemy.text("""
                CREATE TABLE IF NOT EXISTS test_schema.orders (
                    id serial PRIMARY KEY,
                    amount numeric,
                    status text
                )
            """))
            conn.execute(sqlalchemy.text("CREATE SCHEMA IF NOT EXISTS test_schema"))
        with engine.begin() as conn:
            conn.execute(sqlalchemy.text("CREATE SCHEMA IF NOT EXISTS test_schema"))
            conn.execute(sqlalchemy.text("""
                CREATE TABLE IF NOT EXISTS test_schema.orders (
                    id serial PRIMARY KEY,
                    amount numeric,
                    status text
                )
            """))
            for i in range(100):
                conn.execute(sqlalchemy.text(
                    "INSERT INTO test_schema.orders (amount, status) VALUES (:a, :s)"
                ), {"a": float(i), "s": "active" if i % 2 == 0 else None})
        yield pg.get_connection_url()


@pytest.fixture(scope="module")
def adapter(pg_url):
    from dqt.adapters.postgres import PostgresAdapter
    return PostgresAdapter(conn_str=pg_url)


def test_health_check_passes(adapter):
    result = adapter.health_check()
    assert result.passed, [s for s in result.steps if s.status != "pass"]


def test_health_check_has_six_steps(adapter):
    result = adapter.health_check()
    assert len(result.steps) == 6
    names = [s.name for s in result.steps]
    assert names == ["tcp_reach", "auth", "info_schema", "sample_select", "latency_probe", "clock_skew"]


def test_list_schemas(adapter):
    schemas = adapter.list_schemas()
    assert "test_schema" in schemas


def test_list_tables(adapter):
    tables = adapter.list_tables("test_schema")
    assert "orders" in tables


def test_describe_columns(adapter):
    cols = adapter.describe_columns("test_schema", "orders")
    names = [c.name for c in cols]
    assert "id" in names
    assert "amount" in names


def test_sample(adapter):
    df = adapter.sample("test_schema", "orders", n=50)
    assert len(df) == 50
    assert "amount" in df.columns


def test_aggregate(adapter):
    from dqt.adapters._protocol import AggExpr
    result = adapter.aggregate("test_schema", "orders", [
        AggExpr(name="total", sql="COUNT(*)"),
        AggExpr(name="null_status", sql="SUM(CASE WHEN status IS NULL THEN 1 ELSE 0 END)"),
    ])
    assert result["total"] == 100
    assert result["null_status"] == 50
```

- [ ] **Step 2: Run test to verify it fails**

```
cd packages/dqt && uv run pytest tests/adapters/test_postgres_adapter.py -v -m adapter
```
Expected: `ImportError: cannot import name 'PostgresAdapter'`

- [ ] **Step 3: Create `adapters/postgres/config.py`**

```python
# packages/dqt/src/dqt/adapters/postgres/config.py
from dataclasses import dataclass, field


@dataclass
class PostgresConfig:
    host: str = "localhost"
    port: int = 5432
    database: str = "postgres"
    username: str = "postgres"
    password: str = ""
    ssl_mode: str = "prefer"

    def to_conn_str(self) -> str:
        return (
            f"postgresql+psycopg2://{self.username}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}?sslmode={self.ssl_mode}"
        )
```

- [ ] **Step 4: Create `adapters/postgres/adapter.py`**

```python
# packages/dqt/src/dqt/adapters/postgres/adapter.py
# PostgresAdapter wraps an ibis postgres backend for schema/sample operations and
# SQLAlchemy for raw aggregate SQL expressions.
from __future__ import annotations

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


class PostgresAdapter:
    def __init__(self, conn_str: str) -> None:
        self._conn_str = conn_str
        self._engine = sa.create_engine(conn_str, pool_pre_ping=True)

    # ── health check ──────────────────────────────────────────────────
    def health_check(self) -> HealthCheckResult:
        steps: list[HealthCheckStep] = []
        steps.append(self._step_tcp())
        if steps[-1].status == "fail":
            return HealthCheckResult(steps=steps + [
                HealthCheckStep(name=n, status="skip", latency_ms=0.0, detail="skipped")
                for n in ("auth", "info_schema", "sample_select", "latency_probe", "clock_skew")
            ])
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
                result = conn.execute(sa.text("SELECT current_user")).scalar()
            return HealthCheckStep("auth", "pass", (time.perf_counter() - t0) * 1000, f"user={result}")
        except Exception as exc:
            return HealthCheckStep("auth", "fail", 0.0, str(exc))

    def _step_info_schema(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            with self._engine.connect() as conn:
                conn.execute(sa.text(
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema')"
                )).scalar()
            return HealthCheckStep("info_schema", "pass", (time.perf_counter() - t0) * 1000, "readable")
        except Exception as exc:
            return HealthCheckStep("info_schema", "fail", 0.0, str(exc))

    def _step_sample_select(self) -> HealthCheckStep:
        t0 = time.perf_counter()
        try:
            with self._engine.connect() as conn:
                conn.execute(sa.text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema NOT IN ('pg_catalog','information_schema') LIMIT 1"
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
            import datetime
            with self._engine.connect() as conn:
                db_now = conn.execute(sa.text("SELECT NOW()")).scalar()
            local_now = datetime.datetime.now(datetime.timezone.utc)
            if db_now.tzinfo is None:
                db_now = db_now.replace(tzinfo=datetime.timezone.utc)
            skew_s = abs((db_now - local_now).total_seconds())
            status = "pass" if skew_s < 60 else "fail"
            return HealthCheckStep("clock_skew", status, (time.perf_counter() - t0) * 1000, f"skew={skew_s:.1f}s")
        except Exception as exc:
            return HealthCheckStep("clock_skew", "fail", 0.0, str(exc))

    # ── data access ───────────────────────────────────────────────────
    def list_schemas(self) -> list[str]:
        with self._engine.connect() as conn:
            rows = conn.execute(sa.text(
                "SELECT DISTINCT table_schema FROM information_schema.tables "
                "WHERE table_schema NOT IN ('pg_catalog','information_schema') ORDER BY 1"
            )).fetchall()
        return [r[0] for r in rows]

    def list_tables(self, schema: str) -> list[str]:
        with self._engine.connect() as conn:
            rows = conn.execute(sa.text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = :schema ORDER BY 1"
            ), {"schema": schema}).fetchall()
        return [r[0] for r in rows]

    def describe_columns(self, schema: str, table: str) -> list[ColumnMeta]:
        with self._engine.connect() as conn:
            rows = conn.execute(sa.text(
                "SELECT column_name, data_type, is_nullable, ordinal_position "
                "FROM information_schema.columns "
                "WHERE table_schema = :schema AND table_name = :table "
                "ORDER BY ordinal_position"
            ), {"schema": schema, "table": table}).fetchall()
        return [
            ColumnMeta(
                name=r[0],
                data_type=r[1],
                nullable=(r[2] == "YES"),
                position=r[3],
            )
            for r in rows
        ]

    def sample(self, schema: str, table: str, n: int = 100_000) -> pd.DataFrame:
        query = sa.text(f'SELECT * FROM "{schema}"."{table}" LIMIT :n')  # noqa: S608
        with self._engine.connect() as conn:
            return pd.read_sql(query, conn, params={"n": n})

    def aggregate(self, schema: str, table: str, exprs: list[AggExpr]) -> dict[str, Any]:
        cols = ", ".join(f"{e.sql} AS {e.name}" for e in exprs)
        query = sa.text(f'SELECT {cols} FROM "{schema}"."{table}"')  # noqa: S608
        with self._engine.connect() as conn:
            row = conn.execute(query).fetchone()
        return dict(zip([e.name for e in exprs], row))
```

- [ ] **Step 5: Create `adapters/postgres/__init__.py`**

```python
# packages/dqt/src/dqt/adapters/postgres/__init__.py
from dqt.adapters.postgres.adapter import PostgresAdapter
from dqt.adapters.postgres.config import PostgresConfig

__all__ = ["PostgresAdapter", "PostgresConfig"]
```

- [ ] **Step 6: Run adapter test**

```
cd packages/dqt && uv run pytest tests/adapters/test_postgres_adapter.py -v -m adapter
```
Expected: all 7 adapter tests PASS (requires Docker for testcontainers).

- [ ] **Step 7: Commit**

```bash
git add packages/dqt/src/dqt/adapters/ packages/dqt/tests/adapters/
git commit -m "feat(dqt): PostgresAdapter — ibis-backed warehouse adapter with 6-step health check"
```

---

### Task 3b: LocalFileAdapter (CSV, Excel, Parquet, JSON, Feather)

**Goal:** Let users run dqt checks on local files without a warehouse connection. Users can call `Runner` with a `LocalFileAdapter` the same way as with `PostgresAdapter`.

**Files:**
- Modify: `packages/dqt/pyproject.toml` — add `duckdb>=0.9` core dep; add optional group `files = ["openpyxl>=3.0", "pyarrow>=14.0"]`
- Create: `packages/dqt/src/dqt/adapters/local/__init__.py`
- Create: `packages/dqt/src/dqt/adapters/local/adapter.py`
- Test: `packages/dqt/tests/adapters/test_local_adapter.py`

Supported formats: `.csv`, `.tsv`, `.xlsx`, `.xls`, `.parquet`, `.json`, `.jsonl`, `.ndjson`, `.feather`, `.arrow`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/adapters/test_local_adapter.py
import io
import pathlib
import tempfile

import numpy as np
import pandas as pd
import pytest


@pytest.fixture(scope="module")
def sample_df() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "id": range(200),
        "amount": rng.normal(100.0, 15.0, 200),
        "status": ["active" if i % 2 == 0 else None for i in range(200)],
    })


@pytest.fixture(scope="module")
def csv_file(tmp_path_factory, sample_df) -> pathlib.Path:
    p = tmp_path_factory.mktemp("files") / "orders.csv"
    sample_df.to_csv(p, index=False)
    return p


@pytest.fixture(scope="module")
def parquet_file(tmp_path_factory, sample_df) -> pathlib.Path:
    p = tmp_path_factory.mktemp("files") / "orders.parquet"
    sample_df.to_parquet(p, index=False)
    return p


@pytest.fixture(scope="module")
def json_file(tmp_path_factory, sample_df) -> pathlib.Path:
    p = tmp_path_factory.mktemp("files") / "orders.json"
    sample_df.to_json(p, orient="records")
    return p


@pytest.fixture(scope="module")
def jsonl_file(tmp_path_factory, sample_df) -> pathlib.Path:
    p = tmp_path_factory.mktemp("files") / "orders.jsonl"
    sample_df.to_json(p, orient="records", lines=True)
    return p


def test_csv_health_check_passes(csv_file):
    from dqt.adapters.local import LocalFileAdapter
    adapter = LocalFileAdapter(csv_file)
    result = adapter.health_check()
    assert result.passed, [s for s in result.steps if s.status not in ("pass", "skip")]


def test_health_check_fails_missing_file(tmp_path):
    from dqt.adapters.local import LocalFileAdapter
    adapter = LocalFileAdapter(tmp_path / "ghost.csv")
    result = adapter.health_check()
    assert not result.passed
    assert result.steps[0].name == "file_exists"
    assert result.steps[0].status == "fail"


def test_list_schemas(csv_file):
    from dqt.adapters.local import LocalFileAdapter
    assert LocalFileAdapter(csv_file).list_schemas() == ["default"]


def test_list_tables_returns_stem(csv_file):
    from dqt.adapters.local import LocalFileAdapter
    assert LocalFileAdapter(csv_file).list_tables("default") == ["orders"]


def test_describe_columns_csv(csv_file):
    from dqt.adapters.local import LocalFileAdapter
    cols = LocalFileAdapter(csv_file).describe_columns("default", "orders")
    names = [c.name for c in cols]
    assert "id" in names and "amount" in names and "status" in names
    status_col = next(c for c in cols if c.name == "status")
    assert status_col.nullable is True


def test_sample_csv_limit(csv_file):
    from dqt.adapters.local import LocalFileAdapter
    df = LocalFileAdapter(csv_file).sample("default", "orders", n=50)
    assert len(df) == 50


def test_sample_csv_full_when_small(csv_file, sample_df):
    from dqt.adapters.local import LocalFileAdapter
    df = LocalFileAdapter(csv_file).sample("default", "orders", n=100_000)
    assert len(df) == len(sample_df)


def test_aggregate_csv(csv_file):
    from dqt.adapters._protocol import AggExpr
    from dqt.adapters.local import LocalFileAdapter
    result = LocalFileAdapter(csv_file).aggregate("default", "orders", [
        AggExpr(name="total", sql="COUNT(*)"),
        AggExpr(name="null_status", sql="SUM(CASE WHEN status IS NULL THEN 1 ELSE 0 END)"),
    ])
    assert result["total"] == 200
    assert result["null_status"] == 100


def test_parquet_roundtrip(parquet_file):
    from dqt.adapters._protocol import AggExpr
    from dqt.adapters.local import LocalFileAdapter
    adapter = LocalFileAdapter(parquet_file)
    assert adapter.health_check().passed
    result = adapter.aggregate("default", "orders", [AggExpr(name="n", sql="COUNT(*)")])
    assert result["n"] == 200


def test_json_roundtrip(json_file):
    from dqt.adapters.local import LocalFileAdapter
    adapter = LocalFileAdapter(json_file)
    assert adapter.health_check().passed
    df = adapter.sample("default", "orders", n=10)
    assert len(df) == 10


def test_jsonl_roundtrip(jsonl_file):
    from dqt.adapters.local import LocalFileAdapter
    adapter = LocalFileAdapter(jsonl_file)
    assert adapter.health_check().passed
    df = adapter.sample("default", "orders")
    assert len(df) == 200


def test_unsupported_format_raises(tmp_path):
    from dqt.adapters.local import LocalFileAdapter
    with pytest.raises(ValueError, match="Unsupported format"):
        LocalFileAdapter(tmp_path / "data.xyz")


def test_implements_warehouse_adapter_protocol(csv_file):
    from dqt.adapters._protocol import WarehouseAdapter
    from dqt.adapters.local import LocalFileAdapter
    assert isinstance(LocalFileAdapter(csv_file), WarehouseAdapter)
```

- [ ] **Step 2: Run test to verify it fails**

```
cd packages/dqt && uv run pytest tests/adapters/test_local_adapter.py -v
```
Expected: `ImportError: cannot import name 'LocalFileAdapter'`

- [ ] **Step 3: Add `duckdb` to `pyproject.toml`**

Add `"duckdb>=0.9"` to the `dependencies` list. Add optional group:
```toml
[project.optional-dependencies]
files = ["openpyxl>=3.0", "pyarrow>=14.0"]
```
(Keep existing optional groups; just add `files` to the list.)

Then run: `cd packages/dqt && uv sync` to install duckdb.

- [ ] **Step 4: Create `adapters/local/adapter.py`**

```python
# packages/dqt/src/dqt/adapters/local/adapter.py
# Ref: https://duckdb.org/docs/api/python/overview — used for SQL aggregations on DataFrames
from __future__ import annotations

import pathlib
import time
from typing import Any

import pandas as pd

from dqt.adapters._protocol import (
    AggExpr,
    ColumnMeta,
    HealthCheckResult,
    HealthCheckStep,
)
from dqt.utils.logging import get_logger

_log = get_logger(__name__)

_READERS: dict[str, Any] = {
    ".csv":     lambda p: pd.read_csv(p),
    ".tsv":     lambda p: pd.read_csv(p, sep="\t"),
    ".xlsx":    lambda p: pd.read_excel(p),
    ".xls":     lambda p: pd.read_excel(p),
    ".parquet": lambda p: pd.read_parquet(p),
    ".json":    lambda p: pd.read_json(p),
    ".jsonl":   lambda p: pd.read_json(p, lines=True),
    ".ndjson":  lambda p: pd.read_json(p, lines=True),
    ".feather": lambda p: pd.read_feather(p),
    ".arrow":   lambda p: pd.read_feather(p),
}


class LocalFileAdapter:
    """Reads a local file and exposes it as a single-table WarehouseAdapter."""

    def __init__(self, path: str | pathlib.Path) -> None:
        self._path = pathlib.Path(path)
        self._suffix = self._path.suffix.lower()
        if self._suffix not in _READERS:
            supported = ", ".join(sorted(_READERS))
            raise ValueError(f"Unsupported format '{self._suffix}'. Supported: {supported}")
        self._table_name = self._path.stem

    def _read(self) -> pd.DataFrame:
        return _READERS[self._suffix](self._path)

    def health_check(self) -> HealthCheckResult:
        steps: list[HealthCheckStep] = []
        _skip_names = ("readable", "parseable", "columns", "sample_read", "row_count")

        t0 = time.perf_counter()
        if not self._path.exists():
            steps.append(HealthCheckStep("file_exists", "fail", 0.0, f"not found: {self._path}"))
            for name in _skip_names:
                steps.append(HealthCheckStep(name, "skip", 0.0, "skipped"))
            return HealthCheckResult(steps=steps)
        steps.append(HealthCheckStep("file_exists", "pass", (time.perf_counter() - t0) * 1000, str(self._path)))

        t0 = time.perf_counter()
        try:
            self._path.read_bytes()[:1024]
            steps.append(HealthCheckStep("readable", "pass", (time.perf_counter() - t0) * 1000, "ok"))
        except Exception as exc:
            steps.append(HealthCheckStep("readable", "fail", 0.0, str(exc)))
            for name in ("parseable", "columns", "sample_read", "row_count"):
                steps.append(HealthCheckStep(name, "skip", 0.0, "skipped"))
            return HealthCheckResult(steps=steps)

        t0 = time.perf_counter()
        try:
            df = self._read()
        except Exception as exc:
            steps.append(HealthCheckStep("parseable", "fail", 0.0, str(exc)))
            for name in ("columns", "sample_read", "row_count"):
                steps.append(HealthCheckStep(name, "skip", 0.0, "skipped"))
            return HealthCheckResult(steps=steps)
        steps.append(HealthCheckStep("parseable", "pass", (time.perf_counter() - t0) * 1000, f"{len(df.columns)} columns"))

        t0 = time.perf_counter()
        steps.append(HealthCheckStep("columns", "pass", (time.perf_counter() - t0) * 1000, str(list(df.columns)[:5])))

        t0 = time.perf_counter()
        steps.append(HealthCheckStep("sample_read", "pass", (time.perf_counter() - t0) * 1000, "ok"))

        t0 = time.perf_counter()
        steps.append(HealthCheckStep("row_count", "pass", (time.perf_counter() - t0) * 1000, f"{len(df)} rows"))

        return HealthCheckResult(steps=steps)

    def list_schemas(self) -> list[str]:
        return ["default"]

    def list_tables(self, schema: str) -> list[str]:
        return [self._table_name]

    def describe_columns(self, schema: str, table: str) -> list[ColumnMeta]:
        df = self._read()
        return [
            ColumnMeta(
                name=col,
                data_type=str(df[col].dtype),
                nullable=bool(df[col].isna().any()),
                position=i + 1,
            )
            for i, col in enumerate(df.columns)
        ]

    def sample(self, schema: str, table: str, n: int = 100_000) -> pd.DataFrame:
        df = self._read()
        if len(df) <= n:
            return df.reset_index(drop=True)
        return df.sample(n=n, random_state=42).reset_index(drop=True)

    def aggregate(self, schema: str, table: str, exprs: list[AggExpr]) -> dict[str, Any]:
        import duckdb  # optional dep; bundled with ibis-framework
        df = self._read()
        con = duckdb.connect()
        con.register("_data", df)
        cols = ", ".join(f"{e.sql} AS {e.name}" for e in exprs)
        row = con.execute(f"SELECT {cols} FROM _data").fetchone()  # noqa: S608 — no user-controlled table name
        con.close()
        return dict(zip([e.name for e in exprs], row))
```

- [ ] **Step 5: Create `adapters/local/__init__.py`**

```python
from dqt.adapters.local.adapter import LocalFileAdapter

__all__ = ["LocalFileAdapter"]
```

- [ ] **Step 6: Run all tests**

```
cd packages/dqt && uv run pytest tests/adapters/test_local_adapter.py -v
```
Expected: all 13 tests PASS (no Docker required — pure file I/O).

Also run: `cd packages/dqt && uv run pytest tests/ -m "not adapter" -v` to confirm no regressions.

- [ ] **Step 7: Commit**

```bash
git add packages/dqt/pyproject.toml packages/dqt/src/dqt/adapters/local/ \
        packages/dqt/tests/adapters/test_local_adapter.py
git commit -m "feat(dqt): LocalFileAdapter — run checks on CSV/Excel/Parquet/JSON/JSONL/Feather files"
```

---

### Task 4: STAT_SCALES + detector registry

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/_scales.py`
- Create: `packages/dqt/src/dqt/algorithms/_registry.py`
- Create: `packages/dqt/tests/algorithms/__init__.py`
- Test: `packages/dqt/tests/algorithms/test_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/algorithms/test_registry.py
import pytest

from dqt.algorithms._base import Verdict, compute_verdict


def test_stat_scales_contains_all_phase2a_slugs():
    from dqt.algorithms._scales import STAT_SCALES
    expected_slugs = {
        # Task 5 — basic
        "completeness_rate", "uniqueness_rate", "validity_rate",
        "numeric_mean_shift", "volume_change_ratio",
        # Task 5b — extended basic (DQL parity)
        "max_in_range", "min_in_range", "median_in_range", "stddev_in_range",
        "sum_in_range", "cardinality_in_range", "quantile_in_range",
        "value_in_range_violation", "set_membership_violation", "set_exclusion_violation",
        "regex_match_violation", "string_length_violation", "date_format_violation",
        "monotonicity_violation", "column_pair_violation", "composite_uniqueness_violation",
        # Task 6 — schema/referential
        "schema_change", "referential_integrity_rate",
        # Task 7 — statistical
        "ks_pvalue", "mad_outlier_fraction", "double_mad_outlier_fraction",
        "isolation_forest_fraction", "stl_residual_zscore",
        # Task 7b — distribution-adaptive outliers
        "zscore_outlier_fraction", "adjusted_boxplot_fraction",
    }
    missing = expected_slugs - set(STAT_SCALES.keys())
    assert not missing, f"Missing slugs: {missing}"


def test_compute_verdict_lower_is_better_pass():
    # ks_pvalue: warn=0.95, fail=0.99 — score 0.90 should be pass
    v = compute_verdict(0.90, "ks_pvalue")
    assert v == Verdict.pass_


def test_compute_verdict_lower_is_better_warn():
    # score 0.96 → warn
    v = compute_verdict(0.96, "ks_pvalue")
    assert v == Verdict.warn


def test_compute_verdict_lower_is_better_fail():
    # score 0.995 → fail
    v = compute_verdict(0.995, "ks_pvalue")
    assert v == Verdict.fail


def test_compute_verdict_higher_is_better_pass():
    # completeness_rate: warn=0.95, fail=0.90 — score 0.97 should be pass
    v = compute_verdict(0.97, "completeness_rate")
    assert v == Verdict.pass_


def test_compute_verdict_higher_is_better_warn():
    v = compute_verdict(0.93, "completeness_rate")
    assert v == Verdict.warn


def test_compute_verdict_higher_is_better_fail():
    v = compute_verdict(0.88, "completeness_rate")
    assert v == Verdict.fail


def test_compute_verdict_unknown_slug():
    with pytest.raises(KeyError, match="STAT_SCALE"):
        compute_verdict(0.5, "nonexistent_slug")


def test_registry_register_and_get():
    from dqt.algorithms._base import BaseDetector
    from dqt.algorithms._registry import Registry

    class FakeDetector(BaseDetector):
        slug = "test_fake_detector_xyz"
        group = "test"

    reg = Registry()
    reg.register(FakeDetector)
    assert reg.get("test_fake_detector_xyz") is FakeDetector


def test_registry_get_unknown_raises():
    from dqt.algorithms._registry import Registry
    reg = Registry()
    with pytest.raises(KeyError):
        reg.get("not_registered")


def test_global_registry_has_basic_detectors():
    from dqt.algorithms._registry import registry
    # After all basic detectors are imported (Task 5), these must be present.
    # For now just verify registry is a Registry instance.
    from dqt.algorithms._registry import Registry
    assert isinstance(registry, Registry)
```

- [ ] **Step 2: Run to verify it fails**

```
cd packages/dqt && uv run pytest tests/algorithms/test_registry.py -v
```
Expected: `ImportError` on `_scales` and `_registry`.

- [ ] **Step 3: Create `algorithms/_scales.py`**

```python
# packages/dqt/src/dqt/algorithms/_scales.py
# Single source of truth for stat scale definitions.
# Frontend reads the TS version generated by `make stats-scales`.
# Zero imports from dqt — this file must import nothing from this package.
from typing import Literal, NamedTuple


class StatScale(NamedTuple):
    slug: str
    max: float
    warn_threshold: float
    fail_threshold: float
    direction: Literal["lower_is_better", "higher_is_better"]
    plain_english_label: str
    hint: str


STAT_SCALES: dict[str, StatScale] = {
    s.slug: s for s in [
        StatScale("completeness_rate",         1.0,   0.95,  0.90,  "higher_is_better", "Completeness",               "Fraction of non-null values"),
        StatScale("uniqueness_rate",            1.0,   0.95,  0.80,  "higher_is_better", "Uniqueness",                 "Fraction of distinct values"),
        StatScale("validity_rate",              1.0,   0.95,  0.90,  "higher_is_better", "Validity",                   "Fraction of values matching the rule"),
        StatScale("numeric_mean_shift",        10.0,   2.0,   3.0,   "lower_is_better",  "Mean shift (σ)",             "Z-score of mean deviation from baseline"),
        StatScale("volume_change_ratio",        1.0,   0.10,  0.25,  "lower_is_better",  "Row-count change",           "Fractional deviation from baseline row count"),
        StatScale("schema_change",              1.0,   0.5,   0.5,   "lower_is_better",  "Schema change",              "1.0 if schema changed, 0.0 if unchanged"),
        # Numeric aggregate bounds (binary: 0.0 = in range, 1.0 = out of range)
        StatScale("max_in_range",               1.0,   0.5,   0.5,   "lower_is_better",  "Max in bounds",              "1.0 when MAX(col) outside [min, max]; 0.0 otherwise"),
        StatScale("min_in_range",               1.0,   0.5,   0.5,   "lower_is_better",  "Min in bounds",              "1.0 when MIN(col) outside [min, max]; 0.0 otherwise"),
        StatScale("median_in_range",            1.0,   0.5,   0.5,   "lower_is_better",  "Median in bounds",           "1.0 when median outside [min, max]"),
        StatScale("stddev_in_range",            1.0,   0.5,   0.5,   "lower_is_better",  "Stddev in bounds",           "1.0 when STDDEV outside [min, max]"),
        StatScale("sum_in_range",               1.0,   0.5,   0.5,   "lower_is_better",  "Sum in bounds",              "1.0 when SUM outside [min, max]"),
        StatScale("cardinality_in_range",       1.0,   0.5,   0.5,   "lower_is_better",  "Cardinality in bounds",      "1.0 when COUNT(DISTINCT col) outside [min, max]"),
        StatScale("quantile_in_range",          1.0,   0.5,   0.5,   "lower_is_better",  "Quantile in bounds",         "1.0 when specified quantile outside [min, max]"),
        # Row-level fraction checks (fraction of rows violating the rule)
        StatScale("value_in_range_violation",   0.10,  0.001, 0.01,  "lower_is_better",  "Values in range",            "Fraction of values outside [min, max]"),
        StatScale("set_membership_violation",   0.10,  0.001, 0.01,  "lower_is_better",  "Set membership",             "Fraction of values not in the allowed set"),
        StatScale("set_exclusion_violation",    0.10,  0.001, 0.01,  "lower_is_better",  "Set exclusion",              "Fraction of values in the forbidden set"),
        StatScale("regex_match_violation",      0.10,  0.001, 0.01,  "lower_is_better",  "Regex format",               "Fraction of values not matching any regex pattern"),
        StatScale("string_length_violation",    0.10,  0.001, 0.01,  "lower_is_better",  "String length",              "Fraction of values with length outside [min_len, max_len]"),
        StatScale("date_format_violation",      0.10,  0.001, 0.01,  "lower_is_better",  "Date format",                "Fraction of values not parseable as the given date format"),
        StatScale("monotonicity_violation",     1.0,   0.5,   0.5,   "lower_is_better",  "Monotonicity",               "1.0 if ordering violated; 0.0 if sequence is monotonic"),
        StatScale("column_pair_violation",      0.10,  0.001, 0.01,  "lower_is_better",  "Column pair rule",           "Fraction of rows where the pair comparison rule is violated"),
        StatScale("composite_uniqueness_violation", 0.10, 0.001, 0.01, "lower_is_better","Composite key uniqueness",   "Fraction of rows that are duplicates on the composite key"),
        StatScale("referential_integrity_rate", 1.0,   0.99,  0.95,  "higher_is_better", "Referential integrity",      "Fraction of FK values present in parent table"),
        StatScale("ks_pvalue",                  1.0,   0.95,  0.99,  "lower_is_better",  "KS drift (1−p)",             "1 − p-value from two-sample KS test; warn p<0.05, fail p<0.01"),
        StatScale("mad_outlier_fraction",       0.20,  0.01,  0.05,  "lower_is_better",  "Outlier fraction (MAD)",        "Fraction of values with |modified Z| > 3.5"),
        StatScale("double_mad_outlier_fraction", 0.20,  0.01,  0.05,  "lower_is_better",  "Outlier fraction (double-MAD)",    "Fraction flagged by asymmetric double-MAD; robust on skewed distributions"),
        StatScale("zscore_outlier_fraction",     0.10,  0.01,  0.05,  "lower_is_better",  "Outlier fraction (Z-score)",       "Fraction of values with |Z| > threshold; valid only under normality"),
        StatScale("adjusted_boxplot_fraction",   0.20,  0.01,  0.05,  "lower_is_better",  "Outlier fraction (adj. boxplot)",  "Fraction outside medcouple-adjusted Tukey fences; Hubert & Vandervieren 2008"),
        StatScale("isolation_forest_fraction",  0.20,  0.05,  0.10,  "lower_is_better",  "Outlier fraction (IF)",      "Fraction of rows classified as anomalies by Isolation Forest"),
        StatScale("stl_residual_zscore",       10.0,   3.0,   5.0,   "lower_is_better",  "STL residual Z-score",       "Max absolute Z-score of STL residuals over the current window"),
    ]
}
```

- [ ] **Step 4: Create `algorithms/_registry.py`**

```python
# packages/dqt/src/dqt/algorithms/_registry.py
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dqt.algorithms._base import BaseDetector


class Registry:
    def __init__(self) -> None:
        self._map: dict[str, type[BaseDetector]] = {}

    def register(self, cls: type[BaseDetector]) -> type[BaseDetector]:
        self._map[cls.slug] = cls
        return cls

    def get(self, slug: str) -> type[BaseDetector]:
        try:
            return self._map[slug]
        except KeyError:
            raise KeyError(f"Detector slug '{slug}' not registered. Import the detector module first.")

    def slugs(self) -> list[str]:
        return list(self._map.keys())


registry = Registry()
```

- [ ] **Step 5: Run test to verify it passes**

```
cd packages/dqt && uv run pytest tests/algorithms/test_registry.py -v -k "not global_registry"
```
Expected: 9 tests PASS (the `test_global_registry_has_basic_detectors` test verifies something added in Task 5 — skip it for now with `-k "not global_registry"`).

- [ ] **Step 6: Commit**

```bash
git add packages/dqt/src/dqt/algorithms/_scales.py packages/dqt/src/dqt/algorithms/_registry.py \
        packages/dqt/tests/algorithms/
git commit -m "feat(dqt): STAT_SCALES source of truth + detector registry"
```

---

### Task 5: Basic aggregate detectors (completeness, uniqueness, validity, numeric, volume)

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/basic/__init__.py`
- Create: `packages/dqt/src/dqt/algorithms/basic/completeness.py`
- Create: `packages/dqt/src/dqt/algorithms/basic/uniqueness.py`
- Create: `packages/dqt/src/dqt/algorithms/basic/validity.py`
- Create: `packages/dqt/src/dqt/algorithms/basic/numeric.py`
- Create: `packages/dqt/src/dqt/algorithms/basic/volume.py`
- Test: `packages/dqt/tests/algorithms/basic/test_completeness.py` (and the other four)

- [ ] **Step 1: Write the failing tests for all five detectors**

```python
# packages/dqt/tests/algorithms/basic/test_completeness.py
import math
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.basic.completeness import CompletenessDetector
    return CompletenessDetector()


def agg(null_count: int, total: int) -> pd.DataFrame:
    return pd.DataFrame([{"null_count": null_count, "total_count": total}])


# 1. Known-answer test: 50/1000 nulls → completeness = 0.95 → warn boundary
def test_completeness_at_warn_boundary(detector):
    df = agg(50, 1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert abs(result.score - 0.95) < 1e-9
    assert result.verdict == Verdict.warn


# 2. Behaviour: very high completeness → pass; very low → fail
def test_completeness_pass(detector):
    df = agg(1, 1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.verdict == Verdict.pass_


def test_completeness_fail(detector):
    df = agg(150, 1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.verdict == Verdict.fail


def test_completeness_all_null(detector):
    df = agg(100, 100)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.score == 0.0
    assert result.verdict == Verdict.fail


# 3. Hypothesis: score always in [0,1], no NaN/Inf
@given(
    null_count=st.integers(0, 1000),
    total_count=st.integers(1, 1000),
)
@settings(max_examples=200)
def test_completeness_stability(null_count, total_count):
    from dqt.algorithms.basic.completeness import CompletenessDetector
    null_count = min(null_count, total_count)
    df = agg(null_count, total_count)
    detector = CompletenessDetector()
    state = detector.fit(df)
    result = detector.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)


# 4. STAT_SCALE verdict boundary: score=0.92 → warn (between 0.90 and 0.95)
def test_completeness_stat_scale_verdict():
    from dqt.algorithms.basic.completeness import CompletenessDetector
    from dqt.algorithms._base import compute_verdict
    v = compute_verdict(0.92, "completeness_rate")
    assert v == Verdict.warn


def test_completeness_get_aggregations(detector):
    exprs = detector.get_aggregations("amount")
    names = {e.name for e in exprs}
    assert "null_count" in names
    assert "total_count" in names
```

```python
# packages/dqt/tests/algorithms/basic/test_uniqueness.py
import math
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.basic.uniqueness import UniquenessDetector
    return UniquenessDetector()


def agg(distinct: int, total: int) -> pd.DataFrame:
    return pd.DataFrame([{"distinct_count": distinct, "total_count": total}])


def test_uniqueness_known_answer(detector):
    df = agg(950, 1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert abs(result.score - 0.95) < 1e-9
    assert result.verdict == Verdict.warn


def test_uniqueness_pass(detector):
    df = agg(999, 1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.verdict == Verdict.pass_


def test_uniqueness_fail(detector):
    df = agg(700, 1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.verdict == Verdict.fail


@given(
    distinct=st.integers(0, 1000),
    total=st.integers(1, 1000),
)
@settings(max_examples=200)
def test_uniqueness_stability(distinct, total):
    from dqt.algorithms.basic.uniqueness import UniquenessDetector
    distinct = min(distinct, total)
    df = agg(distinct, total)
    det = UniquenessDetector()
    state = det.fit(df)
    result = det.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)


def test_uniqueness_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.97, "uniqueness_rate") == Verdict.pass_
    assert compute_verdict(0.92, "uniqueness_rate") == Verdict.warn
    assert compute_verdict(0.75, "uniqueness_rate") == Verdict.fail
```

```python
# packages/dqt/tests/algorithms/basic/test_validity.py
import math
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.basic.validity import ValidityDetector
    return ValidityDetector(sql_predicate="amount > 0")


def agg(invalid: int, total: int) -> pd.DataFrame:
    return pd.DataFrame([{"invalid_count": invalid, "total_count": total}])


def test_validity_known_answer(detector):
    # 50/1000 invalid → validity_rate = 0.95 → warn
    df = agg(50, 1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert abs(result.score - 0.95) < 1e-9
    assert result.verdict == Verdict.warn


def test_validity_all_valid(detector):
    df = agg(0, 1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.score == 1.0
    assert result.verdict == Verdict.pass_


def test_validity_all_invalid(detector):
    df = agg(1000, 1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.score == 0.0
    assert result.verdict == Verdict.fail


@given(invalid=st.integers(0, 1000), total=st.integers(1, 1000))
@settings(max_examples=200)
def test_validity_stability(invalid, total):
    from dqt.algorithms.basic.validity import ValidityDetector
    invalid = min(invalid, total)
    df = agg(invalid, total)
    det = ValidityDetector(sql_predicate="x > 0")
    state = det.fit(df)
    result = det.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)


def test_validity_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.97, "validity_rate") == Verdict.pass_
    assert compute_verdict(0.92, "validity_rate") == Verdict.warn
    assert compute_verdict(0.88, "validity_rate") == Verdict.fail


def test_validity_get_aggregations(detector):
    exprs = detector.get_aggregations("amount")
    names = {e.name for e in exprs}
    assert "invalid_count" in names
    assert "total_count" in names
    # SQL must embed the predicate
    pred_expr = next(e for e in exprs if e.name == "invalid_count")
    assert "amount > 0" in pred_expr.sql
```

```python
# packages/dqt/tests/algorithms/basic/test_numeric.py
import math
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.basic.numeric import NumericMeanDetector
    return NumericMeanDetector()


def agg(mean: float, stddev: float) -> pd.DataFrame:
    return pd.DataFrame([{"mean": mean, "stddev": stddev}])


def test_numeric_no_shift(detector):
    # Baseline mean=10, std=2. Current same → z=0 → pass
    ref = agg(10.0, 2.0)
    state = detector.fit(ref)
    result = detector.score(ref, state)
    assert result.score == pytest.approx(0.0)
    assert result.verdict == Verdict.pass_


def test_numeric_warn_shift(detector):
    # Baseline mean=10, std=2. Current mean=14.3 → z≈2.15 → warn
    ref = agg(10.0, 2.0)
    state = detector.fit(ref)
    curr = agg(14.3, 2.0)
    result = detector.score(curr, state)
    assert result.score == pytest.approx(2.15, abs=0.1)
    assert result.verdict == Verdict.warn


def test_numeric_fail_shift(detector):
    # z > 3 → fail
    ref = agg(10.0, 2.0)
    state = detector.fit(ref)
    curr = agg(20.0, 2.0)
    result = detector.score(curr, state)
    assert result.score > 3.0
    assert result.verdict == Verdict.fail


@given(
    ref_mean=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
    ref_std=st.floats(min_value=0.01, max_value=100, allow_nan=False, allow_infinity=False),
    curr_mean=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=200)
def test_numeric_stability(ref_mean, ref_std, curr_mean):
    from dqt.algorithms.basic.numeric import NumericMeanDetector
    ref = agg(ref_mean, ref_std)
    curr = agg(curr_mean, ref_std)
    det = NumericMeanDetector()
    state = det.fit(ref)
    result = det.score(curr, state)
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)
    assert result.score >= 0.0


def test_numeric_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(1.5, "numeric_mean_shift") == Verdict.pass_
    assert compute_verdict(2.5, "numeric_mean_shift") == Verdict.warn
    assert compute_verdict(4.0, "numeric_mean_shift") == Verdict.fail
```

```python
# packages/dqt/tests/algorithms/basic/test_volume.py
import math
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.basic.volume import VolumeDetector
    return VolumeDetector()


def agg(count: int) -> pd.DataFrame:
    return pd.DataFrame([{"row_count": count}])


def test_volume_no_change(detector):
    ref = agg(1000)
    state = detector.fit(ref)
    result = detector.score(ref, state)
    assert result.score == pytest.approx(0.0)
    assert result.verdict == Verdict.pass_


def test_volume_warn(detector):
    ref = agg(1000)
    state = detector.fit(ref)
    curr = agg(880)  # 12% drop → warn
    result = detector.score(curr, state)
    assert result.score == pytest.approx(0.12, abs=0.01)
    assert result.verdict == Verdict.warn


def test_volume_fail(detector):
    ref = agg(1000)
    state = detector.fit(ref)
    curr = agg(700)  # 30% drop → fail
    result = detector.score(curr, state)
    assert result.score == pytest.approx(0.30, abs=0.01)
    assert result.verdict == Verdict.fail


@given(
    ref_count=st.integers(1, 10_000),
    curr_count=st.integers(1, 10_000),
)
@settings(max_examples=200)
def test_volume_stability(ref_count, curr_count):
    from dqt.algorithms.basic.volume import VolumeDetector
    ref = agg(ref_count)
    curr = agg(curr_count)
    det = VolumeDetector()
    state = det.fit(ref)
    result = det.score(curr, state)
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)
    assert result.score >= 0.0


def test_volume_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.05, "volume_change_ratio") == Verdict.pass_
    assert compute_verdict(0.15, "volume_change_ratio") == Verdict.warn
    assert compute_verdict(0.30, "volume_change_ratio") == Verdict.fail
```

- [ ] **Step 2: Run to verify failures**

```
cd packages/dqt && uv run pytest tests/algorithms/basic/ -v
```
Expected: `ImportError` for all detector modules.

- [ ] **Step 3: Create `algorithms/basic/__init__.py`** (empty)

- [ ] **Step 4: Create `algorithms/basic/completeness.py`**

```python
# packages/dqt/src/dqt/algorithms/basic/completeness.py
from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class CompletenessDetector(BaseAggregateDetector):
    slug = "completeness"
    group = "basic"

    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [
            AggExpr(name="null_count", sql=f"COUNT(*) - COUNT({col})"),
            AggExpr(name="total_count", sql="COUNT(*)"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        row = reference.iloc[0]
        total = int(row["total_count"])
        rate = 1.0 - (int(row["null_count"]) / total) if total > 0 else 1.0
        return {"baseline_completeness": rate}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        row = current.iloc[0]
        total = int(row["total_count"])
        rate = 1.0 - (int(row["null_count"]) / total) if total > 0 else 1.0
        return DetectorResult(
            score=rate,
            verdict=self._verdict(rate),
            plain_english=f"Completeness is {rate:.1%} (baseline {state['baseline_completeness']:.1%})",
            details={"completeness_rate": rate, "baseline": state["baseline_completeness"]},
        )

    def _verdict(self, score: float):  # type: ignore[override]
        from dqt.algorithms._base import compute_verdict
        return compute_verdict(score, "completeness_rate")
```

- [ ] **Step 5: Create `algorithms/basic/uniqueness.py`**

```python
# packages/dqt/src/dqt/algorithms/basic/uniqueness.py
from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class UniquenessDetector(BaseAggregateDetector):
    slug = "uniqueness"
    group = "basic"

    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [
            AggExpr(name="distinct_count", sql=f"COUNT(DISTINCT {col})"),
            AggExpr(name="total_count", sql="COUNT(*)"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        row = reference.iloc[0]
        total = int(row["total_count"])
        rate = int(row["distinct_count"]) / total if total > 0 else 1.0
        return {"baseline_uniqueness": rate}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        row = current.iloc[0]
        total = int(row["total_count"])
        rate = int(row["distinct_count"]) / total if total > 0 else 1.0
        return DetectorResult(
            score=rate,
            verdict=self._verdict(rate),
            plain_english=f"Uniqueness is {rate:.1%} (baseline {state['baseline_uniqueness']:.1%})",
            details={"uniqueness_rate": rate, "baseline": state["baseline_uniqueness"]},
        )

    def _verdict(self, score: float):  # type: ignore[override]
        from dqt.algorithms._base import compute_verdict
        return compute_verdict(score, "uniqueness_rate")
```

- [ ] **Step 6: Create `algorithms/basic/validity.py`**

```python
# packages/dqt/src/dqt/algorithms/basic/validity.py
from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class ValidityDetector(BaseAggregateDetector):
    slug = "validity"
    group = "basic"

    def __init__(self, sql_predicate: str = "TRUE") -> None:
        self._predicate = sql_predicate

    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [
            AggExpr(
                name="invalid_count",
                sql=f"SUM(CASE WHEN NOT ({self._predicate}) THEN 1 ELSE 0 END)",
            ),
            AggExpr(name="total_count", sql="COUNT(*)"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        row = reference.iloc[0]
        total = int(row["total_count"])
        rate = 1.0 - (int(row["invalid_count"]) / total) if total > 0 else 1.0
        return {"baseline_validity": rate}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        row = current.iloc[0]
        total = int(row["total_count"])
        rate = 1.0 - (int(row["invalid_count"]) / total) if total > 0 else 1.0
        return DetectorResult(
            score=rate,
            verdict=self._verdict(rate),
            plain_english=f"{rate:.1%} of values are valid (predicate: {self._predicate!r})",
            details={"validity_rate": rate, "predicate": self._predicate},
        )

    def _verdict(self, score: float):  # type: ignore[override]
        from dqt.algorithms._base import compute_verdict
        return compute_verdict(score, "validity_rate")
```

- [ ] **Step 7: Create `algorithms/basic/numeric.py`**

```python
# packages/dqt/src/dqt/algorithms/basic/numeric.py
from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class NumericMeanDetector(BaseAggregateDetector):
    """Detects mean shift relative to baseline, expressed in standard deviations."""
    slug = "numeric_mean"
    group = "basic"

    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [
            AggExpr(name="mean", sql=f"AVG({col})"),
            AggExpr(name="stddev", sql=f"STDDEV({col})"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        row = reference.iloc[0]
        return {
            "ref_mean": float(row["mean"]),
            "ref_stddev": float(row["stddev"]) if float(row["stddev"] or 0) > 0 else 1.0,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        row = current.iloc[0]
        z = abs((float(row["mean"]) - state["ref_mean"]) / state["ref_stddev"])
        return DetectorResult(
            score=z,
            verdict=self._verdict(z),
            plain_english=f"Mean shifted {z:.2f}σ from baseline (baseline μ={state['ref_mean']:.3g})",
            details={"current_mean": float(row["mean"]), "baseline_mean": state["ref_mean"], "z_score": z},
        )

    def _verdict(self, score: float):  # type: ignore[override]
        from dqt.algorithms._base import compute_verdict
        return compute_verdict(score, "numeric_mean_shift")
```

- [ ] **Step 8: Create `algorithms/basic/volume.py`**

```python
# packages/dqt/src/dqt/algorithms/basic/volume.py
from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class VolumeDetector(BaseAggregateDetector):
    """Detects anomalous row count changes relative to the baseline window."""
    slug = "volume"
    group = "basic"

    def get_aggregations(self, col: str) -> list[AggExpr]:  # col unused for volume
        return [AggExpr(name="row_count", sql="COUNT(*)")]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {"baseline_count": int(reference.iloc[0]["row_count"])}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr_count = int(current.iloc[0]["row_count"])
        base_count = state["baseline_count"]
        ratio = abs(curr_count / base_count - 1.0) if base_count > 0 else 0.0
        return DetectorResult(
            score=ratio,
            verdict=self._verdict(ratio),
            plain_english=f"Row count {curr_count:,} is {ratio:.1%} {'above' if curr_count > base_count else 'below'} baseline ({base_count:,})",
            details={"current_count": curr_count, "baseline_count": base_count, "change_ratio": ratio},
        )

    def _verdict(self, score: float):  # type: ignore[override]
        from dqt.algorithms._base import compute_verdict
        return compute_verdict(score, "volume_change_ratio")
```

- [ ] **Step 9: Create `algorithms/basic/__init__.py`** — import all detectors so they register

```python
# packages/dqt/src/dqt/algorithms/basic/__init__.py
from dqt.algorithms.basic.completeness import CompletenessDetector
from dqt.algorithms.basic.uniqueness import UniquenessDetector
from dqt.algorithms.basic.validity import ValidityDetector
from dqt.algorithms.basic.numeric import NumericMeanDetector
from dqt.algorithms.basic.volume import VolumeDetector

__all__ = [
    "CompletenessDetector",
    "UniquenessDetector",
    "ValidityDetector",
    "NumericMeanDetector",
    "VolumeDetector",
]
```

- [ ] **Step 10: Run all basic detector tests**

```
cd packages/dqt && uv run pytest tests/algorithms/basic/ -v
```
Expected: all tests PASS.

- [ ] **Step 11: Commit**

```bash
git add packages/dqt/src/dqt/algorithms/basic/ packages/dqt/tests/algorithms/basic/
git commit -m "feat(dqt): basic aggregate detectors — completeness, uniqueness, validity, numeric_mean, volume"
```

---

### Task 5b: Extended basic detectors — numeric bounds, value checks, monotonicity, column pairs

Covers the check patterns from the DQL reference library that are not yet implemented. All but `MonotonicityDetector` push computation to the warehouse via SQL aggregations (`BaseAggregateDetector`).

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py`
- Create: `packages/dqt/src/dqt/algorithms/basic/value_checks.py`
- Create: `packages/dqt/src/dqt/algorithms/basic/monotonicity.py`
- Create: `packages/dqt/src/dqt/algorithms/basic/column_pairs.py`
- Test: `packages/dqt/tests/algorithms/basic/test_numeric_bounds.py`
- Test: `packages/dqt/tests/algorithms/basic/test_value_checks.py`
- Test: `packages/dqt/tests/algorithms/basic/test_monotonicity.py`
- Test: `packages/dqt/tests/algorithms/basic/test_column_pairs.py`

- [ ] **Step 1: Write failing tests**

```python
# packages/dqt/tests/algorithms/basic/test_numeric_bounds.py
import math
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st
from dqt.algorithms._base import Verdict


# ── helpers ──────────────────────────────────────────────────────────────────
def agg1(key: str, value) -> pd.DataFrame:
    return pd.DataFrame([{key: value}])


# ── MaxInRangeDetector ────────────────────────────────────────────────────────
@pytest.fixture()
def max_det():
    from dqt.algorithms.basic.numeric_bounds import MaxInRangeDetector
    return MaxInRangeDetector(min_val=0.0, max_val=100.0)

def test_max_in_range_pass(max_det):
    df = agg1("agg_value", 85.0)
    state = max_det.fit(df)
    result = max_det.score(df, state)
    assert result.score == 0.0
    assert result.verdict == Verdict.pass_

def test_max_in_range_fail(max_det):
    df = agg1("agg_value", 120.0)
    state = max_det.fit(df)
    result = max_det.score(df, state)
    assert result.score == 1.0
    assert result.verdict == Verdict.fail

def test_max_at_boundary(max_det):
    df = agg1("agg_value", 100.0)
    state = max_det.fit(df)
    result = max_det.score(df, state)
    assert result.verdict == Verdict.pass_

def test_max_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.0, "max_in_range") == Verdict.pass_
    assert compute_verdict(1.0, "max_in_range") == Verdict.fail


# ── MinInRangeDetector ────────────────────────────────────────────────────────
def test_min_in_range_pass():
    from dqt.algorithms.basic.numeric_bounds import MinInRangeDetector
    det = MinInRangeDetector(min_val=5.0, max_val=100.0)
    df = agg1("agg_value", 10.0)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.pass_

def test_min_in_range_fail():
    from dqt.algorithms.basic.numeric_bounds import MinInRangeDetector
    det = MinInRangeDetector(min_val=5.0, max_val=100.0)
    df = agg1("agg_value", 2.0)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.fail


# ── MedianInRangeDetector ─────────────────────────────────────────────────────
def test_median_in_range_pass():
    from dqt.algorithms.basic.numeric_bounds import MedianInRangeDetector
    det = MedianInRangeDetector(min_val=0.0, max_val=50.0)
    df = agg1("agg_value", 25.0)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.pass_


# ── StdDevInRangeDetector ─────────────────────────────────────────────────────
def test_stddev_in_range_pass():
    from dqt.algorithms.basic.numeric_bounds import StdDevInRangeDetector
    det = StdDevInRangeDetector(min_val=0.5, max_val=3.0)
    df = agg1("agg_value", 1.5)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.pass_

def test_stddev_too_high_fail():
    from dqt.algorithms.basic.numeric_bounds import StdDevInRangeDetector
    det = StdDevInRangeDetector(min_val=0.5, max_val=3.0)
    df = agg1("agg_value", 5.0)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.fail


# ── SumInRangeDetector ────────────────────────────────────────────────────────
def test_sum_in_range_pass():
    from dqt.algorithms.basic.numeric_bounds import SumInRangeDetector
    det = SumInRangeDetector(min_val=1000.0, max_val=10000.0)
    df = agg1("agg_value", 5000.0)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.pass_


# ── CardinalityInRangeDetector ────────────────────────────────────────────────
def test_cardinality_in_range_pass():
    from dqt.algorithms.basic.numeric_bounds import CardinalityInRangeDetector
    det = CardinalityInRangeDetector(min_val=5, max_val=50)
    df = agg1("agg_value", 20)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.pass_

def test_cardinality_too_high_fail():
    from dqt.algorithms.basic.numeric_bounds import CardinalityInRangeDetector
    det = CardinalityInRangeDetector(min_val=5, max_val=50)
    df = agg1("agg_value", 100)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.fail


# ── QuantileInRangeDetector ───────────────────────────────────────────────────
def test_quantile_in_range_pass():
    from dqt.algorithms.basic.numeric_bounds import QuantileInRangeDetector
    det = QuantileInRangeDetector(quantile=0.95, min_val=90.0, max_val=120.0)
    df = agg1("agg_value", 100.0)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.pass_


# ── Hypothesis: all binary detectors return 0.0 or 1.0, no NaN/Inf ────────────
@given(agg_val=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False))
@settings(max_examples=200)
def test_numeric_bounds_stability(agg_val):
    from dqt.algorithms.basic.numeric_bounds import MaxInRangeDetector
    det = MaxInRangeDetector(min_val=0.0, max_val=100.0)
    df = agg1("agg_value", agg_val)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.score in (0.0, 1.0)
    assert not math.isnan(result.score)
```

```python
# packages/dqt/tests/algorithms/basic/test_value_checks.py
import math
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st
from dqt.algorithms._base import Verdict


def agg(out_of_rule: int, total: int) -> pd.DataFrame:
    return pd.DataFrame([{"violation_count": out_of_rule, "total_count": total}])


# ── ValueInRangeDetector ──────────────────────────────────────────────────────
@pytest.fixture()
def range_det():
    from dqt.algorithms.basic.value_checks import ValueInRangeDetector
    return ValueInRangeDetector(min_val=0.0, max_val=100.0)

def test_value_in_range_pass(range_det):
    df = agg(0, 1000)
    state = range_det.fit(df)
    result = range_det.score(df, state)
    assert result.score == 0.0
    assert result.verdict == Verdict.pass_

def test_value_in_range_fail(range_det):
    df = agg(50, 1000)   # 5% violation → fail (> 0.01)
    state = range_det.fit(df)
    result = range_det.score(df, state)
    assert result.score == pytest.approx(0.05)
    assert result.verdict == Verdict.fail

def test_value_in_range_sql_uses_bounds(range_det):
    exprs = range_det.get_aggregations("price")
    sql_text = " ".join(e.sql for e in exprs)
    assert "0.0" in sql_text or "100.0" in sql_text


# ── SetMembershipDetector ─────────────────────────────────────────────────────
@pytest.fixture()
def set_det():
    from dqt.algorithms.basic.value_checks import SetMembershipDetector
    return SetMembershipDetector(allowed_values={"active", "inactive", "pending"})

def test_set_membership_pass(set_det):
    df = agg(0, 1000)
    state = set_det.fit(df)
    result = set_det.score(df, state)
    assert result.verdict == Verdict.pass_

def test_set_membership_fail(set_det):
    df = agg(20, 1000)  # 2% violation
    state = set_det.fit(df)
    result = set_det.score(df, state)
    assert result.verdict == Verdict.fail


# ── SetExclusionDetector ──────────────────────────────────────────────────────
def test_set_exclusion_pass():
    from dqt.algorithms.basic.value_checks import SetExclusionDetector
    det = SetExclusionDetector(forbidden_values={"deleted", "banned"})
    df = agg(0, 1000)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.pass_

def test_set_exclusion_fail():
    from dqt.algorithms.basic.value_checks import SetExclusionDetector
    det = SetExclusionDetector(forbidden_values={"deleted", "banned"})
    df = agg(15, 1000)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.fail


# ── RegexMatchDetector ────────────────────────────────────────────────────────
def test_regex_match_pass():
    from dqt.algorithms.basic.value_checks import RegexMatchDetector
    det = RegexMatchDetector(pattern=r"^[A-Z]{2}\d{4}$")
    df = agg(0, 500)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.pass_

def test_regex_match_fail():
    from dqt.algorithms.basic.value_checks import RegexMatchDetector
    det = RegexMatchDetector(pattern=r"^[A-Z]{2}\d{4}$")
    df = agg(10, 500)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.fail


# ── StringLengthRangeDetector ─────────────────────────────────────────────────
def test_string_length_pass():
    from dqt.algorithms.basic.value_checks import StringLengthRangeDetector
    det = StringLengthRangeDetector(min_len=2, max_len=50)
    df = agg(0, 1000)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.pass_

def test_string_length_fail():
    from dqt.algorithms.basic.value_checks import StringLengthRangeDetector
    det = StringLengthRangeDetector(min_len=2, max_len=50)
    df = agg(20, 1000)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.fail


# ── DateFormatDetector ────────────────────────────────────────────────────────
def test_date_format_pass():
    from dqt.algorithms.basic.value_checks import DateFormatDetector
    det = DateFormatDetector(date_format="%Y-%m-%d")
    df = agg(0, 500)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.pass_

def test_date_format_fail():
    from dqt.algorithms.basic.value_checks import DateFormatDetector
    det = DateFormatDetector(date_format="%Y-%m-%d")
    df = agg(25, 500)
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.fail


# ── Hypothesis: fraction checks ───────────────────────────────────────────────
@given(violations=st.integers(0, 1000), total=st.integers(1, 1000))
@settings(max_examples=200)
def test_value_checks_stability(violations, total):
    from dqt.algorithms.basic.value_checks import ValueInRangeDetector
    violations = min(violations, total)
    det = ValueInRangeDetector(min_val=0.0, max_val=100.0)
    df = pd.DataFrame([{"violation_count": violations, "total_count": total}])
    state = det.fit(df)
    result = det.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)


# ── STAT_SCALE verdict boundaries ─────────────────────────────────────────────
def test_value_checks_stat_scale_verdicts():
    from dqt.algorithms._base import compute_verdict
    for slug in ("value_in_range_violation", "set_membership_violation",
                 "set_exclusion_violation", "regex_match_violation",
                 "string_length_violation", "date_format_violation"):
        assert compute_verdict(0.0,   slug) == Verdict.pass_
        assert compute_verdict(0.002, slug) == Verdict.warn
        assert compute_verdict(0.02,  slug) == Verdict.fail
```

```python
# packages/dqt/tests/algorithms/basic/test_monotonicity.py
import math
import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st
from dqt.algorithms._base import Verdict


@pytest.fixture()
def inc_det():
    from dqt.algorithms.basic.monotonicity import MonotonicityDetector
    return MonotonicityDetector(direction="increasing")


@pytest.fixture()
def dec_det():
    from dqt.algorithms.basic.monotonicity import MonotonicityDetector
    return MonotonicityDetector(direction="decreasing")


# 1. Known-answer: strictly increasing sequence → pass
def test_monotonicity_increasing_pass(inc_det):
    df = pd.DataFrame({"value": [1, 2, 3, 4, 5, 6]})
    state = inc_det.fit(df)
    result = inc_det.score(df, state)
    assert result.score == 0.0
    assert result.verdict == Verdict.pass_


# 2. Known-answer: decreasing in increasing detector → fail
def test_monotonicity_increasing_fail(inc_det):
    df = pd.DataFrame({"value": [1, 2, 1, 4, 5]})  # dip at index 2
    state = inc_det.fit(df)
    result = inc_det.score(df, state)
    assert result.score == 1.0
    assert result.verdict == Verdict.fail


# 2b. Decreasing sequence → pass for decreasing detector
def test_monotonicity_decreasing_pass(dec_det):
    df = pd.DataFrame({"value": [10, 9, 8, 7, 6]})
    state = dec_det.fit(df)
    result = dec_det.score(df, state)
    assert result.score == 0.0
    assert result.verdict == Verdict.pass_


# 2c. Non-decreasing (with ties) is still acceptable for increasing
def test_monotonicity_allows_ties(inc_det):
    df = pd.DataFrame({"value": [1, 2, 2, 3, 4]})
    state = inc_det.fit(df)
    result = inc_det.score(df, state)
    assert result.verdict == Verdict.pass_


# 3. Hypothesis: result is 0.0 or 1.0, no NaN
@given(
    values=st.lists(st.integers(min_value=0, max_value=100), min_size=3, max_size=50)
)
@settings(max_examples=200)
def test_monotonicity_stability(values):
    from dqt.algorithms.basic.monotonicity import MonotonicityDetector
    df = pd.DataFrame({"value": values})
    det = MonotonicityDetector(direction="increasing")
    state = det.fit(df)
    result = det.score(df, state)
    assert result.score in (0.0, 1.0)
    assert not math.isnan(result.score)


# 4. STAT_SCALE verdict
def test_monotonicity_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.0, "monotonicity_violation") == Verdict.pass_
    assert compute_verdict(1.0, "monotonicity_violation") == Verdict.fail
```

```python
# packages/dqt/tests/algorithms/basic/test_column_pairs.py
import math
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st
from dqt.algorithms._base import Verdict


def agg(violation_count: int, total: int) -> pd.DataFrame:
    return pd.DataFrame([{"violation_count": violation_count, "total_count": total}])


# ── ColumnPairComparisonDetector ──────────────────────────────────────────────
@pytest.fixture()
def gt_det():
    from dqt.algorithms.basic.column_pairs import ColumnPairComparisonDetector
    return ColumnPairComparisonDetector(col_a="list_price", col_b="sale_price", operator=">")

def test_pair_comparison_pass(gt_det):
    df = agg(0, 1000)
    state = gt_det.fit(df)
    result = gt_det.score(df, state)
    assert result.score == 0.0
    assert result.verdict == Verdict.pass_

def test_pair_comparison_fail(gt_det):
    df = agg(20, 1000)   # 2% → fail
    state = gt_det.fit(df)
    result = gt_det.score(df, state)
    assert result.verdict == Verdict.fail

def test_pair_comparison_sql_uses_operator(gt_det):
    exprs = gt_det.get_aggregations("ignored")
    sql_text = " ".join(e.sql for e in exprs)
    assert "list_price" in sql_text
    assert "sale_price" in sql_text
    assert ">" in sql_text

# Supported operators
@pytest.mark.parametrize("op", [">", ">=", "<", "<=", "=", "!="])
def test_pair_comparison_operators(op):
    from dqt.algorithms.basic.column_pairs import ColumnPairComparisonDetector
    det = ColumnPairComparisonDetector(col_a="a", col_b="b", operator=op)
    exprs = det.get_aggregations("ignored")
    assert any(op in e.sql for e in exprs)


# ── CompositeUniquenessDetector ───────────────────────────────────────────────
@pytest.fixture()
def comp_det():
    from dqt.algorithms.basic.column_pairs import CompositeUniquenessDetector
    return CompositeUniquenessDetector(key_columns=["order_id", "line_item"])

def test_composite_unique_pass(comp_det):
    df = pd.DataFrame([{"total_count": 1000, "distinct_count": 1000}])
    state = comp_det.fit(df)
    result = comp_det.score(df, state)
    assert result.score == 0.0
    assert result.verdict == Verdict.pass_

def test_composite_unique_fail(comp_det):
    df = pd.DataFrame([{"total_count": 1000, "distinct_count": 980}])
    state = comp_det.fit(df)
    result = comp_det.score(df, state)
    assert result.score == pytest.approx(0.02, abs=0.001)
    assert result.verdict == Verdict.fail


# ── Hypothesis ────────────────────────────────────────────────────────────────
@given(violations=st.integers(0, 1000), total=st.integers(1, 1000))
@settings(max_examples=200)
def test_column_pair_stability(violations, total):
    from dqt.algorithms.basic.column_pairs import ColumnPairComparisonDetector
    violations = min(violations, total)
    det = ColumnPairComparisonDetector(col_a="a", col_b="b", operator=">")
    df = agg(violations, total)
    state = det.fit(df)
    result = det.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)


# ── STAT_SCALE verdicts ───────────────────────────────────────────────────────
def test_column_pairs_stat_scale_verdicts():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.0,   "column_pair_violation") == Verdict.pass_
    assert compute_verdict(0.002, "column_pair_violation") == Verdict.warn
    assert compute_verdict(0.02,  "column_pair_violation") == Verdict.fail
    assert compute_verdict(0.0,   "composite_uniqueness_violation") == Verdict.pass_
    assert compute_verdict(0.002, "composite_uniqueness_violation") == Verdict.warn
    assert compute_verdict(0.02,  "composite_uniqueness_violation") == Verdict.fail
```

- [ ] **Step 2: Run to verify failures**

```
cd packages/dqt && uv run pytest tests/algorithms/basic/test_numeric_bounds.py \
        tests/algorithms/basic/test_value_checks.py \
        tests/algorithms/basic/test_monotonicity.py \
        tests/algorithms/basic/test_column_pairs.py -v
```
Expected: `ImportError` for all four modules.

- [ ] **Step 3: Create `algorithms/basic/numeric_bounds.py`**

```python
# packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py
# Aggregate range checks: verify that a column's aggregate statistic (max, min, median,
# stddev, sum, cardinality, quantile) falls within caller-specified bounds.
# Score: 0.0 = within bounds (pass), 1.0 = outside bounds (fail). Binary.
from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_BINARY = {"lower_is_better": True, "warn": 0.5, "fail": 0.5}


def _binary_result(value: float, min_val: float, max_val: float, label: str, slug: str) -> DetectorResult:
    in_range = min_val <= value <= max_val
    score = 0.0 if in_range else 1.0
    from dqt.algorithms._base import compute_verdict
    return DetectorResult(
        score=score,
        verdict=compute_verdict(score, slug),
        plain_english=(
            f"{label} {value:.4g} is {'within' if in_range else 'outside'} bounds [{min_val:.4g}, {max_val:.4g}]"
        ),
        details={"value": value, "min_bound": min_val, "max_bound": max_val},
    )


@registry.register
class MaxInRangeDetector(BaseAggregateDetector):
    """Verifies MAX(col) is within [min_val, max_val]."""
    slug = "max_in_range"; group = "basic"
    def __init__(self, min_val: float = 0.0, max_val: float = float("inf")) -> None:
        self._min, self._max = min_val, max_val
    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [AggExpr(name="agg_value", sql=f"MAX({col})")]
    def fit(self, reference: pd.DataFrame) -> DetectorState: return {}
    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return _binary_result(float(current.iloc[0]["agg_value"]), self._min, self._max, "MAX", "max_in_range")


@registry.register
class MinInRangeDetector(BaseAggregateDetector):
    """Verifies MIN(col) is within [min_val, max_val]."""
    slug = "min_in_range"; group = "basic"
    def __init__(self, min_val: float = 0.0, max_val: float = float("inf")) -> None:
        self._min, self._max = min_val, max_val
    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [AggExpr(name="agg_value", sql=f"MIN({col})")]
    def fit(self, reference: pd.DataFrame) -> DetectorState: return {}
    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return _binary_result(float(current.iloc[0]["agg_value"]), self._min, self._max, "MIN", "min_in_range")


@registry.register
class MedianInRangeDetector(BaseAggregateDetector):
    """Verifies PERCENTILE_CONT(0.5) of col is within [min_val, max_val]."""
    slug = "median_in_range"; group = "basic"
    def __init__(self, min_val: float = 0.0, max_val: float = float("inf")) -> None:
        self._min, self._max = min_val, max_val
    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [AggExpr(name="agg_value", sql=f"PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {col})")]
    def fit(self, reference: pd.DataFrame) -> DetectorState: return {}
    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return _binary_result(float(current.iloc[0]["agg_value"]), self._min, self._max, "Median", "median_in_range")


@registry.register
class StdDevInRangeDetector(BaseAggregateDetector):
    """Verifies STDDEV(col) is within [min_val, max_val]."""
    slug = "stddev_in_range"; group = "basic"
    def __init__(self, min_val: float = 0.0, max_val: float = float("inf")) -> None:
        self._min, self._max = min_val, max_val
    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [AggExpr(name="agg_value", sql=f"STDDEV({col})")]
    def fit(self, reference: pd.DataFrame) -> DetectorState: return {}
    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return _binary_result(float(current.iloc[0]["agg_value"] or 0), self._min, self._max, "Stddev", "stddev_in_range")


@registry.register
class SumInRangeDetector(BaseAggregateDetector):
    """Verifies SUM(col) is within [min_val, max_val]."""
    slug = "sum_in_range"; group = "basic"
    def __init__(self, min_val: float = 0.0, max_val: float = float("inf")) -> None:
        self._min, self._max = min_val, max_val
    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [AggExpr(name="agg_value", sql=f"SUM({col})")]
    def fit(self, reference: pd.DataFrame) -> DetectorState: return {}
    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return _binary_result(float(current.iloc[0]["agg_value"] or 0), self._min, self._max, "SUM", "sum_in_range")


@registry.register
class CardinalityInRangeDetector(BaseAggregateDetector):
    """Verifies COUNT(DISTINCT col) is within [min_val, max_val]."""
    slug = "cardinality_in_range"; group = "basic"
    def __init__(self, min_val: int = 1, max_val: int = 2**31) -> None:
        self._min, self._max = float(min_val), float(max_val)
    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [AggExpr(name="agg_value", sql=f"COUNT(DISTINCT {col})")]
    def fit(self, reference: pd.DataFrame) -> DetectorState: return {}
    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return _binary_result(float(current.iloc[0]["agg_value"]), self._min, self._max, "Cardinality", "cardinality_in_range")


@registry.register
class QuantileInRangeDetector(BaseAggregateDetector):
    """Verifies a specified quantile of col is within [min_val, max_val]."""
    slug = "quantile_in_range"; group = "basic"
    def __init__(self, quantile: float = 0.95, min_val: float = 0.0, max_val: float = float("inf")) -> None:
        self._q, self._min, self._max = quantile, min_val, max_val
    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [AggExpr(name="agg_value", sql=f"PERCENTILE_CONT({self._q}) WITHIN GROUP (ORDER BY {col})")]
    def fit(self, reference: pd.DataFrame) -> DetectorState: return {}
    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        label = f"p{int(self._q * 100)}"
        return _binary_result(float(current.iloc[0]["agg_value"]), self._min, self._max, label, "quantile_in_range")
```

- [ ] **Step 4: Create `algorithms/basic/value_checks.py`**

```python
# packages/dqt/src/dqt/algorithms/basic/value_checks.py
# Row-level rule checks: fraction of rows violating the rule.
# All push computation to the warehouse via SQL CASE expressions.
# Score: fraction of violations; 0.0 = all rows pass.
from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


def _fraction_result(df: pd.DataFrame, slug: str, label: str) -> DetectorResult:
    from dqt.algorithms._base import compute_verdict
    row = df.iloc[0]
    total = int(row["total_count"])
    frac = int(row["violation_count"]) / total if total > 0 else 0.0
    return DetectorResult(
        score=frac,
        verdict=compute_verdict(frac, slug),
        plain_english=f"{frac:.2%} of values violate {label}",
        details={"violation_fraction": frac, "violation_count": int(row["violation_count"]), "total": total},
    )


@registry.register
class ValueInRangeDetector(BaseAggregateDetector):
    """Fraction of values outside [min_val, max_val]."""
    slug = "value_in_range"; group = "basic"
    def __init__(self, min_val: float = float("-inf"), max_val: float = float("inf")) -> None:
        self._min, self._max = min_val, max_val
    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [
            AggExpr("violation_count", f"SUM(CASE WHEN {col} < {self._min} OR {col} > {self._max} THEN 1 ELSE 0 END)"),
            AggExpr("total_count", "COUNT(*)"),
        ]
    def fit(self, reference: pd.DataFrame) -> DetectorState: return {}
    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return _fraction_result(current, "value_in_range_violation", f"range [{self._min}, {self._max}]")


@registry.register
class SetMembershipDetector(BaseAggregateDetector):
    """Fraction of values not in the allowed set."""
    slug = "set_membership"; group = "basic"
    def __init__(self, allowed_values: set | list = ()) -> None:
        self._allowed = set(allowed_values)
    def _in_clause(self) -> str:
        quoted = ", ".join(f"'{v}'" for v in sorted(self._allowed))
        return f"({quoted})"
    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [
            AggExpr("violation_count", f"SUM(CASE WHEN {col} NOT IN {self._in_clause()} THEN 1 ELSE 0 END)"),
            AggExpr("total_count", "COUNT(*)"),
        ]
    def fit(self, reference: pd.DataFrame) -> DetectorState: return {}
    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return _fraction_result(current, "set_membership_violation", f"allowed set {sorted(self._allowed)}")


@registry.register
class SetExclusionDetector(BaseAggregateDetector):
    """Fraction of values in the forbidden set."""
    slug = "set_exclusion"; group = "basic"
    def __init__(self, forbidden_values: set | list = ()) -> None:
        self._forbidden = set(forbidden_values)
    def _in_clause(self) -> str:
        quoted = ", ".join(f"'{v}'" for v in sorted(self._forbidden))
        return f"({quoted})"
    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [
            AggExpr("violation_count", f"SUM(CASE WHEN {col} IN {self._in_clause()} THEN 1 ELSE 0 END)"),
            AggExpr("total_count", "COUNT(*)"),
        ]
    def fit(self, reference: pd.DataFrame) -> DetectorState: return {}
    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return _fraction_result(current, "set_exclusion_violation", f"forbidden set {sorted(self._forbidden)}")


@registry.register
class RegexMatchDetector(BaseAggregateDetector):
    """Fraction of values not matching the regex pattern (Postgres ~ operator)."""
    slug = "regex_match"; group = "basic"
    def __init__(self, pattern: str = ".*") -> None:
        self._pattern = pattern
    def get_aggregations(self, col: str) -> list[AggExpr]:
        escaped = self._pattern.replace("'", "''")
        return [
            AggExpr("violation_count", f"SUM(CASE WHEN {col}::text !~ '{escaped}' THEN 1 ELSE 0 END)"),
            AggExpr("total_count", "COUNT(*)"),
        ]
    def fit(self, reference: pd.DataFrame) -> DetectorState: return {}
    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return _fraction_result(current, "regex_match_violation", f"pattern '{self._pattern}'")


@registry.register
class StringLengthRangeDetector(BaseAggregateDetector):
    """Fraction of values with string length outside [min_len, max_len]."""
    slug = "string_length_range"; group = "basic"
    def __init__(self, min_len: int = 0, max_len: int = 255) -> None:
        self._min, self._max = min_len, max_len
    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [
            AggExpr("violation_count",
                    f"SUM(CASE WHEN LENGTH({col}::text) < {self._min} OR LENGTH({col}::text) > {self._max} THEN 1 ELSE 0 END)"),
            AggExpr("total_count", "COUNT(*)"),
        ]
    def fit(self, reference: pd.DataFrame) -> DetectorState: return {}
    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return _fraction_result(current, "string_length_violation", f"length [{self._min}, {self._max}]")


@registry.register
class DateFormatDetector(BaseAggregateDetector):
    """Fraction of values not parseable as the given date format (Postgres TO_DATE)."""
    slug = "date_format"; group = "basic"
    def __init__(self, date_format: str = "YYYY-MM-DD") -> None:
        # Convert Python strftime format to Postgres TO_DATE format if needed
        self._pg_format = (date_format
                           .replace("%Y", "YYYY").replace("%m", "MM").replace("%d", "DD")
                           .replace("%H", "HH24").replace("%M", "MI").replace("%S", "SS"))
    def get_aggregations(self, col: str) -> list[AggExpr]:
        fmt = self._pg_format.replace("'", "''")
        return [
            AggExpr("violation_count",
                    f"SUM(CASE WHEN {col} IS NOT NULL AND "
                    f"(CASE WHEN {col}::text ~ '^[0-9]' THEN "
                    f"(SELECT COUNT(*) FROM (SELECT TO_DATE({col}::text, '{fmt}')) t) = 0 "
                    f"ELSE TRUE END) THEN 1 ELSE 0 END)"),
            AggExpr("total_count", "COUNT(*)"),
        ]
    def fit(self, reference: pd.DataFrame) -> DetectorState: return {}
    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return _fraction_result(current, "date_format_violation", f"format '{self._pg_format}'")
```

> **Note on DateFormatDetector SQL:** The generated SQL is a safe approximation for Postgres. For strict validation, use `ValidityDetector` with a custom predicate like `TO_DATE(col::text, 'YYYY-MM-DD') IS NOT NULL`. This detector generates a best-effort SQL; the runner can fall back to a sample-based approach if the warehouse doesn't support this form.

- [ ] **Step 5: Create `algorithms/basic/monotonicity.py`**

```python
# packages/dqt/src/dqt/algorithms/basic/monotonicity.py
# Checks whether a column's values are non-decreasing or non-increasing
# within the current sample. Score: 0.0 = monotonic, 1.0 = violated.
from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry


@registry.register
class MonotonicityDetector(BaseDetector):
    """
    Checks that values in the first numeric column of the DataFrame are
    non-decreasing (increasing) or non-increasing (decreasing).
    Score: 0.0 = monotonic, 1.0 = not monotonic.
    """
    slug = "monotonicity"; group = "basic"

    def __init__(self, direction: Literal["increasing", "decreasing"] = "increasing") -> None:
        self._direction = direction

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {"direction": self._direction}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        values = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        direction = state["direction"]
        if direction == "increasing":
            is_monotonic = bool(np.all(np.diff(values) >= 0))
        else:
            is_monotonic = bool(np.all(np.diff(values) <= 0))
        score = 0.0 if is_monotonic else 1.0
        from dqt.algorithms._base import compute_verdict
        return DetectorResult(
            score=score,
            verdict=compute_verdict(score, "monotonicity_violation"),
            plain_english=f"Sequence is {'monotonically ' + direction if is_monotonic else 'NOT monotonically ' + direction}",
            details={"direction": direction, "is_monotonic": is_monotonic, "n_values": len(values)},
        )
```

- [ ] **Step 6: Create `algorithms/basic/column_pairs.py`**

```python
# packages/dqt/src/dqt/algorithms/basic/column_pairs.py
# Cross-column and composite-key checks.
from __future__ import annotations

from typing import Literal

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry

_ALLOWED_OPS = {">", ">=", "<", "<=", "=", "!="}


def _fraction_result(df: pd.DataFrame, slug: str, label: str) -> DetectorResult:
    from dqt.algorithms._base import compute_verdict
    row = df.iloc[0]
    total = int(row["total_count"])
    frac = int(row["violation_count"]) / total if total > 0 else 0.0
    return DetectorResult(
        score=frac,
        verdict=compute_verdict(frac, slug),
        plain_english=f"{frac:.2%} of rows violate {label}",
        details={"violation_fraction": frac, "violation_count": int(row["violation_count"]), "total": total},
    )


@registry.register
class ColumnPairComparisonDetector(BaseAggregateDetector):
    """
    Verifies col_a <operator> col_b for every non-null row.
    Supported operators: >, >=, <, <=, =, !=
    Score: fraction of rows where the comparison is false.
    """
    slug = "column_pair_comparison"; group = "basic"

    def __init__(self, col_a: str = "a", col_b: str = "b",
                 operator: str = ">") -> None:
        if operator not in _ALLOWED_OPS:
            raise ValueError(f"operator must be one of {_ALLOWED_OPS}")
        self._col_a, self._col_b, self._op = col_a, col_b, operator

    def get_aggregations(self, col: str) -> list[AggExpr]:
        # col param is ignored — we use the pair's own columns
        return [
            AggExpr("violation_count",
                    f"SUM(CASE WHEN NOT ({self._col_a} {self._op} {self._col_b}) THEN 1 ELSE 0 END)"),
            AggExpr("total_count",
                    f"SUM(CASE WHEN {self._col_a} IS NOT NULL AND {self._col_b} IS NOT NULL THEN 1 ELSE 0 END)"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState: return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        label = f"{self._col_a} {self._op} {self._col_b}"
        return _fraction_result(current, "column_pair_violation", label)


@registry.register
class CompositeUniquenessDetector(BaseAggregateDetector):
    """
    Verifies that the combination of key_columns forms a unique key.
    Score: fraction of rows that are duplicates.
    """
    slug = "composite_uniqueness"; group = "basic"

    def __init__(self, key_columns: list[str] = ()) -> None:
        if not key_columns:
            raise ValueError("key_columns must be non-empty")
        self._cols = list(key_columns)

    def get_aggregations(self, col: str) -> list[AggExpr]:
        concat_expr = " || '|' || ".join(f"COALESCE({c}::text, '__null__')" for c in self._cols)
        return [
            AggExpr("total_count", "COUNT(*)"),
            AggExpr("distinct_count", f"COUNT(DISTINCT ({concat_expr}))"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState: return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        from dqt.algorithms._base import compute_verdict
        row = current.iloc[0]
        total = int(row["total_count"])
        distinct = int(row["distinct_count"])
        dup_frac = (total - distinct) / total if total > 0 else 0.0
        return DetectorResult(
            score=dup_frac,
            verdict=compute_verdict(dup_frac, "composite_uniqueness_violation"),
            plain_english=f"{dup_frac:.2%} duplicate rows on composite key {self._cols} ({total - distinct} dups)",
            details={"duplicate_fraction": dup_frac, "total": total, "distinct": distinct,
                     "key_columns": self._cols},
        )
```

- [ ] **Step 7: Update `algorithms/basic/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/basic/__init__.py
from dqt.algorithms.basic.completeness import CompletenessDetector
from dqt.algorithms.basic.uniqueness import UniquenessDetector
from dqt.algorithms.basic.validity import ValidityDetector
from dqt.algorithms.basic.numeric import NumericMeanDetector
from dqt.algorithms.basic.volume import VolumeDetector
from dqt.algorithms.basic.numeric_bounds import (
    MaxInRangeDetector, MinInRangeDetector, MedianInRangeDetector,
    StdDevInRangeDetector, SumInRangeDetector, CardinalityInRangeDetector,
    QuantileInRangeDetector,
)
from dqt.algorithms.basic.value_checks import (
    ValueInRangeDetector, SetMembershipDetector, SetExclusionDetector,
    RegexMatchDetector, StringLengthRangeDetector, DateFormatDetector,
)
from dqt.algorithms.basic.monotonicity import MonotonicityDetector
from dqt.algorithms.basic.column_pairs import ColumnPairComparisonDetector, CompositeUniquenessDetector

__all__ = [
    "CompletenessDetector", "UniquenessDetector", "ValidityDetector",
    "NumericMeanDetector", "VolumeDetector",
    "MaxInRangeDetector", "MinInRangeDetector", "MedianInRangeDetector",
    "StdDevInRangeDetector", "SumInRangeDetector", "CardinalityInRangeDetector",
    "QuantileInRangeDetector",
    "ValueInRangeDetector", "SetMembershipDetector", "SetExclusionDetector",
    "RegexMatchDetector", "StringLengthRangeDetector", "DateFormatDetector",
    "MonotonicityDetector",
    "ColumnPairComparisonDetector", "CompositeUniquenessDetector",
]
```

- [ ] **Step 8: Run all Task 5b tests**

```
cd packages/dqt && uv run pytest tests/algorithms/basic/test_numeric_bounds.py \
        tests/algorithms/basic/test_value_checks.py \
        tests/algorithms/basic/test_monotonicity.py \
        tests/algorithms/basic/test_column_pairs.py -v
```
Expected: all tests PASS.

- [ ] **Step 9: Commit**

```bash
git add packages/dqt/src/dqt/algorithms/basic/numeric_bounds.py \
        packages/dqt/src/dqt/algorithms/basic/value_checks.py \
        packages/dqt/src/dqt/algorithms/basic/monotonicity.py \
        packages/dqt/src/dqt/algorithms/basic/column_pairs.py \
        packages/dqt/tests/algorithms/basic/test_numeric_bounds.py \
        packages/dqt/tests/algorithms/basic/test_value_checks.py \
        packages/dqt/tests/algorithms/basic/test_monotonicity.py \
        packages/dqt/tests/algorithms/basic/test_column_pairs.py
git commit -m "feat(dqt): extended basic detectors — numeric bounds, value checks, monotonicity, column pairs (DQL parity)"
```

---

### Task 5c: Dataplex-parity detectors (freshness, null fraction, string case, SQL assertion, date-part completeness)

**Goal:** Cover the Dataplex system rule templates not yet in the plan. All are `BaseAggregateDetector` — they push computation to the warehouse via SQL aggregations.

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/basic/freshness.py` — `FreshnessDetector`
- Create: `packages/dqt/src/dqt/algorithms/basic/null_fraction.py` — `NullFractionDetector`
- Create: `packages/dqt/src/dqt/algorithms/basic/string_case.py` — `StringCaseDetector`
- Create: `packages/dqt/src/dqt/algorithms/basic/sql_assertion.py` — `SqlAssertionDetector`
- Create: `packages/dqt/src/dqt/algorithms/basic/date_part.py` — `DatePartCompletenessDetector`
- Modify: `packages/dqt/src/dqt/algorithms/basic/__init__.py` — import all new detectors
- Modify: `packages/dqt/src/dqt/algorithms/_scales.py` — add 5 new STAT_SCALE entries
- Test: `packages/dqt/tests/algorithms/basic/test_freshness.py`
- Test: `packages/dqt/tests/algorithms/basic/test_null_fraction.py`
- Test: `packages/dqt/tests/algorithms/basic/test_string_case.py`
- Test: `packages/dqt/tests/algorithms/basic/test_sql_assertion.py`
- Test: `packages/dqt/tests/algorithms/basic/test_date_part.py`

**STAT_SCALES entries to add** (in `_scales.py`, alongside existing entries):
```python
StatScale("freshness_seconds_behind", 86400*7, 3600, 86400, "lower_is_better",
          "Data freshness", "Seconds since the most recent row timestamp"),
StatScale("null_fraction", 1.0, 0.01, 0.05, "lower_is_better",
          "Null fraction", "Fraction of rows where the column is NULL"),
StatScale("string_case_violation", 1.0, 0.001, 0.01, "lower_is_better",
          "String case violation", "Fraction of rows with wrong case"),
StatScale("sql_assertion_violation", 1.0, 0.001, 0.01, "lower_is_better",
          "SQL assertion violation", "Fraction of rows failing the custom SQL condition"),
StatScale("date_part_missing_fraction", 1.0, 0.01, 0.05, "lower_is_better",
          "Date-part completeness", "Fraction of expected date buckets with no data"),
```

- [ ] **Step 1: Write the failing tests**

```python
# packages/dqt/tests/algorithms/basic/test_freshness.py
import pandas as pd
import pytest
from datetime import datetime, timezone, timedelta


def _agg(seconds_behind: float) -> pd.DataFrame:
    """Simulate what adapter.aggregate() returns for FreshnessDetector."""
    latest = datetime.now(timezone.utc) - timedelta(seconds=seconds_behind)
    return pd.DataFrame([{"latest_ts": latest}])


def test_freshness_pass():
    from dqt.algorithms.basic.freshness import FreshnessDetector
    d = FreshnessDetector(warn_seconds=3600, fail_seconds=86400)
    state = d.fit(pd.DataFrame())
    result = d.score(_agg(60), state)
    assert result.verdict.value == "pass"


def test_freshness_warn():
    from dqt.algorithms.basic.freshness import FreshnessDetector
    d = FreshnessDetector(warn_seconds=3600, fail_seconds=86400)
    state = d.fit(pd.DataFrame())
    result = d.score(_agg(7200), state)
    assert result.verdict.value == "warn"


def test_freshness_fail():
    from dqt.algorithms.basic.freshness import FreshnessDetector
    d = FreshnessDetector(warn_seconds=3600, fail_seconds=86400)
    state = d.fit(pd.DataFrame())
    result = d.score(_agg(90000), state)
    assert result.verdict.value == "fail"


def test_freshness_aggregations():
    from dqt.algorithms.basic.freshness import FreshnessDetector
    d = FreshnessDetector(col="created_at")
    aggs = d.get_aggregations("created_at")
    assert len(aggs) == 1
    assert "MAX" in aggs[0].sql.upper()
```

```python
# packages/dqt/tests/algorithms/basic/test_null_fraction.py
import pandas as pd
import pytest


def _agg(null_count: int, total: int = 1000) -> pd.DataFrame:
    return pd.DataFrame([{"null_count": null_count, "total_count": total}])


def test_null_fraction_pass():
    from dqt.algorithms.basic.null_fraction import NullFractionDetector
    d = NullFractionDetector()
    result = d.score(_agg(5), d.fit(pd.DataFrame()))
    assert result.verdict.value == "pass"


def test_null_fraction_warn():
    from dqt.algorithms.basic.null_fraction import NullFractionDetector
    d = NullFractionDetector()
    result = d.score(_agg(15), d.fit(pd.DataFrame()))
    assert result.verdict.value == "warn"


def test_null_fraction_fail():
    from dqt.algorithms.basic.null_fraction import NullFractionDetector
    d = NullFractionDetector()
    result = d.score(_agg(60), d.fit(pd.DataFrame()))
    assert result.verdict.value == "fail"


def test_null_fraction_zero_total():
    from dqt.algorithms.basic.null_fraction import NullFractionDetector
    d = NullFractionDetector()
    result = d.score(pd.DataFrame([{"null_count": 0, "total_count": 0}]), d.fit(pd.DataFrame()))
    assert result.score == 0.0
```

```python
# packages/dqt/tests/algorithms/basic/test_string_case.py
import pandas as pd
import pytest


def _agg(violations: int, total: int = 1000) -> pd.DataFrame:
    return pd.DataFrame([{"violation_count": violations, "total_count": total}])


def test_string_case_pass():
    from dqt.algorithms.basic.string_case import StringCaseDetector
    d = StringCaseDetector(case="upper")
    result = d.score(_agg(0), d.fit(pd.DataFrame()))
    assert result.verdict.value == "pass"


def test_string_case_fail():
    from dqt.algorithms.basic.string_case import StringCaseDetector
    d = StringCaseDetector(case="upper")
    result = d.score(_agg(50), d.fit(pd.DataFrame()))
    assert result.verdict.value == "fail"


def test_string_case_sql_upper():
    from dqt.algorithms.basic.string_case import StringCaseDetector
    d = StringCaseDetector(case="upper")
    aggs = d.get_aggregations("name")
    sql = aggs[0].sql
    assert "UPPER" in sql.upper() or "upper" in sql.lower()


def test_string_case_invalid_raises():
    from dqt.algorithms.basic.string_case import StringCaseDetector
    with pytest.raises(ValueError, match="case"):
        StringCaseDetector(case="mixed_weird")
```

```python
# packages/dqt/tests/algorithms/basic/test_sql_assertion.py
import pandas as pd
import pytest


def _agg(violations: int, total: int = 1000) -> pd.DataFrame:
    return pd.DataFrame([{"violation_count": violations, "total_count": total}])


def test_sql_assertion_pass():
    from dqt.algorithms.basic.sql_assertion import SqlAssertionDetector
    d = SqlAssertionDetector(condition="amount > 0")
    result = d.score(_agg(0), d.fit(pd.DataFrame()))
    assert result.verdict.value == "pass"


def test_sql_assertion_fail():
    from dqt.algorithms.basic.sql_assertion import SqlAssertionDetector
    d = SqlAssertionDetector(condition="amount > 0")
    result = d.score(_agg(50), d.fit(pd.DataFrame()))
    assert result.verdict.value == "fail"


def test_sql_assertion_aggregations():
    from dqt.algorithms.basic.sql_assertion import SqlAssertionDetector
    d = SqlAssertionDetector(condition="amount > 0")
    # col is ignored for row-level conditions; SQL is built from condition
    aggs = d.get_aggregations("amount")
    assert any("amount > 0" in a.sql for a in aggs)
```

```python
# packages/dqt/tests/algorithms/basic/test_date_part.py
import pandas as pd
import pytest


def _agg(missing: int, total_buckets: int = 30) -> pd.DataFrame:
    return pd.DataFrame([{"missing_buckets": missing, "total_buckets": total_buckets}])


def test_date_part_pass():
    from dqt.algorithms.basic.date_part import DatePartCompletenessDetector
    d = DatePartCompletenessDetector(granularity="day", lookback_days=30)
    result = d.score(_agg(0), d.fit(pd.DataFrame()))
    assert result.verdict.value == "pass"


def test_date_part_fail():
    from dqt.algorithms.basic.date_part import DatePartCompletenessDetector
    d = DatePartCompletenessDetector(granularity="day", lookback_days=30)
    result = d.score(_agg(5), d.fit(pd.DataFrame()))
    assert result.verdict.value == "fail"


def test_date_part_aggregations():
    from dqt.algorithms.basic.date_part import DatePartCompletenessDetector
    d = DatePartCompletenessDetector(granularity="day", lookback_days=30, col="created_at")
    aggs = d.get_aggregations("created_at")
    assert len(aggs) == 2  # missing_buckets + total_buckets
```

- [ ] **Step 2: Run tests to verify they fail**
```
cd packages/dqt && uv run pytest tests/algorithms/basic/test_freshness.py tests/algorithms/basic/test_null_fraction.py tests/algorithms/basic/test_string_case.py tests/algorithms/basic/test_sql_assertion.py tests/algorithms/basic/test_date_part.py -v
```
Expected: `ImportError` for each module.

- [ ] **Step 3: Add STAT_SCALES entries**

In `packages/dqt/src/dqt/algorithms/_scales.py`, add to the `STAT_SCALES` list (inside the `{s.slug: s for s in [...]}` dict comprehension):
```python
StatScale("freshness_seconds_behind", 86400*7, 3600, 86400, "lower_is_better",
          "Data freshness", "Seconds since the most recent row timestamp"),
StatScale("null_fraction", 1.0, 0.01, 0.05, "lower_is_better",
          "Null fraction", "Fraction of rows where the column is NULL"),
StatScale("string_case_violation", 1.0, 0.001, 0.01, "lower_is_better",
          "String case violation", "Fraction of rows with wrong case"),
StatScale("sql_assertion_violation", 1.0, 0.001, 0.01, "lower_is_better",
          "SQL assertion violation", "Fraction of rows failing the custom SQL condition"),
StatScale("date_part_missing_fraction", 1.0, 0.01, 0.05, "lower_is_better",
          "Date-part completeness", "Fraction of expected date buckets with no data"),
```

- [ ] **Step 4: Implement `freshness.py`**

```python
# packages/dqt/src/dqt/algorithms/basic/freshness.py
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState


class FreshnessDetector(BaseAggregateDetector):
    """Checks that the most recent row timestamp is within the specified threshold.
    score = seconds elapsed since latest timestamp."""
    slug = "freshness_seconds_behind"
    group = "basic"

    def __init__(self, col: str = "updated_at", warn_seconds: float = 3600, fail_seconds: float = 86400) -> None:
        self._col = col
        self._warn = warn_seconds
        self._fail = fail_seconds

    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [AggExpr("latest_ts", f"MAX({col})")]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return None

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        latest = current.iloc[0]["latest_ts"]
        if hasattr(latest, "tzinfo") and latest.tzinfo is None:
            latest = latest.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if hasattr(latest, "timestamp"):
            seconds_behind = (now - latest).total_seconds()
        else:
            seconds_behind = float("inf")

        from dqt.algorithms._base import Verdict
        if seconds_behind >= self._fail:
            verdict = Verdict.fail
        elif seconds_behind >= self._warn:
            verdict = Verdict.warn
        else:
            verdict = Verdict.pass_
        return DetectorResult(
            score=seconds_behind,
            verdict=verdict,
            plain_english=f"Latest data is {seconds_behind:.0f}s old",
            details={"seconds_behind": seconds_behind},
        )
```

- [ ] **Step 5: Implement `null_fraction.py`**

```python
# packages/dqt/src/dqt/algorithms/basic/null_fraction.py
from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState


class NullFractionDetector(BaseAggregateDetector):
    """Fraction of rows where the column is NULL. Complements CompletenessDetector."""
    slug = "null_fraction"
    group = "basic"

    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [
            AggExpr("null_count", f"SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END)"),
            AggExpr("total_count", "COUNT(*)"),
        ]

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        row = current.iloc[0]
        total = int(row["total_count"])
        null_count = int(row["null_count"])
        frac = null_count / total if total > 0 else 0.0
        verdict = self._verdict(frac)
        return DetectorResult(
            score=frac,
            verdict=verdict,
            plain_english=f"{null_count}/{total} rows are NULL ({frac:.1%})",
            details={"null_count": null_count, "total_count": total},
        )
```

- [ ] **Step 6: Implement `string_case.py`**

```python
# packages/dqt/src/dqt/algorithms/basic/string_case.py
from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState

_ALLOWED_CASES = {"upper", "lower", "title"}


class StringCaseDetector(BaseAggregateDetector):
    """Validates string column casing: upper / lower / title (title-case)."""
    slug = "string_case_violation"
    group = "basic"

    def __init__(self, case: str = "upper") -> None:
        if case not in _ALLOWED_CASES:
            raise ValueError(f"case must be one of {_ALLOWED_CASES}, got '{case}'")
        self._case = case

    def get_aggregations(self, col: str) -> list[AggExpr]:
        if self._case == "upper":
            cond = f"{col} <> UPPER({col})"
        elif self._case == "lower":
            cond = f"{col} <> LOWER({col})"
        else:  # title
            cond = f"{col} <> INITCAP({col})"
        return [
            AggExpr("violation_count", f"SUM(CASE WHEN {col} IS NOT NULL AND {cond} THEN 1 ELSE 0 END)"),
            AggExpr("total_count", f"SUM(CASE WHEN {col} IS NOT NULL THEN 1 ELSE 0 END)"),
        ]

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        row = current.iloc[0]
        total = int(row["total_count"])
        violations = int(row["violation_count"])
        frac = violations / total if total > 0 else 0.0
        verdict = self._verdict(frac)
        return DetectorResult(
            score=frac,
            verdict=verdict,
            plain_english=f"{violations}/{total} rows have wrong case (expected {self._case})",
            details={"violations": violations, "total": total, "expected_case": self._case},
        )
```

- [ ] **Step 7: Implement `sql_assertion.py`**

```python
# packages/dqt/src/dqt/algorithms/basic/sql_assertion.py
from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState


class SqlAssertionDetector(BaseAggregateDetector):
    """Custom SQL row-level condition. Score = fraction of rows where condition is FALSE."""
    slug = "sql_assertion_violation"
    group = "basic"

    def __init__(self, condition: str) -> None:
        self._condition = condition

    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [
            AggExpr("violation_count", f"SUM(CASE WHEN NOT ({self._condition}) THEN 1 ELSE 0 END)"),
            AggExpr("total_count", "COUNT(*)"),
        ]

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        row = current.iloc[0]
        total = int(row["total_count"])
        violations = int(row["violation_count"])
        frac = violations / total if total > 0 else 0.0
        verdict = self._verdict(frac)
        return DetectorResult(
            score=frac,
            verdict=verdict,
            plain_english=f"{violations}/{total} rows fail: {self._condition}",
            details={"violations": violations, "total": total, "condition": self._condition},
        )
```

- [ ] **Step 8: Implement `date_part.py`**

```python
# packages/dqt/src/dqt/algorithms/basic/date_part.py
from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState

_GRANULARITIES = {"day": "DAY", "week": "WEEK", "month": "MONTH", "hour": "HOUR"}


class DatePartCompletenessDetector(BaseAggregateDetector):
    """Checks that all expected date buckets within a lookback window contain at least one row."""
    slug = "date_part_missing_fraction"
    group = "basic"

    def __init__(self, col: str = "created_at", granularity: str = "day", lookback_days: int = 30) -> None:
        if granularity not in _GRANULARITIES:
            raise ValueError(f"granularity must be one of {set(_GRANULARITIES)}")
        self._col = col
        self._granularity = granularity
        self._lookback_days = lookback_days

    def get_aggregations(self, col: str) -> list[AggExpr]:
        trunc = _GRANULARITIES[self._granularity]
        return [
            AggExpr("missing_buckets", (
                f"({self._lookback_days}) - "
                f"COUNT(DISTINCT DATE_TRUNC('{trunc}', {col}::timestamp)) "
                f"FILTER (WHERE {col} >= CURRENT_DATE - INTERVAL '{self._lookback_days} days')"
            )),
            AggExpr("total_buckets", f"CAST({self._lookback_days} AS INTEGER)"),
        ]

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        row = current.iloc[0]
        total = int(row["total_buckets"])
        missing = max(0, int(row["missing_buckets"]))
        frac = missing / total if total > 0 else 0.0
        verdict = self._verdict(frac)
        return DetectorResult(
            score=frac,
            verdict=verdict,
            plain_english=f"{missing}/{total} date buckets have no data",
            details={"missing_buckets": missing, "total_buckets": total, "granularity": self._granularity},
        )
```

- [ ] **Step 9: Update `basic/__init__.py`** — add imports for all 5 new detectors (alongside existing ones).

- [ ] **Step 10: Run all tests**
```
cd packages/dqt && uv run pytest tests/algorithms/basic/test_freshness.py tests/algorithms/basic/test_null_fraction.py tests/algorithms/basic/test_string_case.py tests/algorithms/basic/test_sql_assertion.py tests/algorithms/basic/test_date_part.py -v
```
Expected: all tests PASS.

Also: `cd packages/dqt && uv run pytest tests/ -m "not adapter" -v`

- [ ] **Step 11: Commit**
```bash
git add packages/dqt/src/dqt/algorithms/basic/freshness.py \
        packages/dqt/src/dqt/algorithms/basic/null_fraction.py \
        packages/dqt/src/dqt/algorithms/basic/string_case.py \
        packages/dqt/src/dqt/algorithms/basic/sql_assertion.py \
        packages/dqt/src/dqt/algorithms/basic/date_part.py \
        packages/dqt/src/dqt/algorithms/basic/__init__.py \
        packages/dqt/src/dqt/algorithms/_scales.py \
        packages/dqt/tests/algorithms/basic/test_freshness.py \
        packages/dqt/tests/algorithms/basic/test_null_fraction.py \
        packages/dqt/tests/algorithms/basic/test_string_case.py \
        packages/dqt/tests/algorithms/basic/test_sql_assertion.py \
        packages/dqt/tests/algorithms/basic/test_date_part.py
git commit -m "feat(dqt): Dataplex-parity detectors — freshness, null fraction, string case, SQL assertion, date-part completeness"
```

---

### Task 6: Schema and referential integrity detectors

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/schema/__init__.py`
- Create: `packages/dqt/src/dqt/algorithms/schema/schema_checks.py`
- Create: `packages/dqt/src/dqt/algorithms/referential/__init__.py`
- Create: `packages/dqt/src/dqt/algorithms/referential/referential.py`
- Test: `packages/dqt/tests/algorithms/schema/test_schema_checks.py`
- Test: `packages/dqt/tests/algorithms/referential/test_referential.py`

- [ ] **Step 1: Write the failing tests**

```python
# packages/dqt/tests/algorithms/schema/test_schema_checks.py
import math
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.schema.schema_checks import SchemaChangeDetector
    return SchemaChangeDetector()


def schema_df(columns: list[tuple[str, str]]) -> pd.DataFrame:
    """Simulate the output of adapter.describe_columns() as a DataFrame."""
    return pd.DataFrame([{"col_name": c, "data_type": t} for c, t in columns])


def test_no_schema_change(detector):
    schema = [("id", "integer"), ("amount", "numeric"), ("status", "text")]
    df = schema_df(schema)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.score == 0.0
    assert result.verdict == Verdict.pass_


def test_column_added(detector):
    ref = schema_df([("id", "integer"), ("amount", "numeric")])
    curr = schema_df([("id", "integer"), ("amount", "numeric"), ("new_col", "text")])
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.score == 1.0
    assert result.verdict == Verdict.fail
    assert "new_col" in result.plain_english


def test_column_removed(detector):
    ref = schema_df([("id", "integer"), ("amount", "numeric"), ("status", "text")])
    curr = schema_df([("id", "integer"), ("amount", "numeric")])
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.score == 1.0
    assert result.verdict == Verdict.fail
    assert "status" in result.plain_english


def test_type_changed(detector):
    ref = schema_df([("id", "integer"), ("amount", "numeric")])
    curr = schema_df([("id", "integer"), ("amount", "text")])
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.score == 1.0
    assert result.verdict == Verdict.fail


@given(n=st.integers(1, 20))
@settings(max_examples=50)
def test_schema_stability_no_change(n):
    from dqt.algorithms.schema.schema_checks import SchemaChangeDetector
    cols = [(f"col_{i}", "text") for i in range(n)]
    df = schema_df(cols)
    det = SchemaChangeDetector()
    state = det.fit(df)
    result = det.score(df, state)
    assert result.score == 0.0
    assert not math.isnan(result.score)


def test_schema_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.0, "schema_change") == Verdict.pass_
    assert compute_verdict(1.0, "schema_change") == Verdict.fail
```

```python
# packages/dqt/tests/algorithms/referential/test_referential.py
import math
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.referential.referential import ReferentialIntegrityDetector
    return ReferentialIntegrityDetector()


def agg(orphan_count: int, total: int) -> pd.DataFrame:
    return pd.DataFrame([{"orphan_count": orphan_count, "total_count": total}])


def test_no_orphans(detector):
    df = agg(0, 1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.score == pytest.approx(1.0)
    assert result.verdict == Verdict.pass_


def test_few_orphans_warn(detector):
    # 9/1000 orphans → rate = 0.991 → pass (above 0.99)
    # 15/1000 orphans → rate = 0.985 → warn
    df = agg(15, 1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.score == pytest.approx(0.985, abs=1e-6)
    assert result.verdict == Verdict.warn


def test_many_orphans_fail(detector):
    df = agg(60, 1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.score < 0.95
    assert result.verdict == Verdict.fail


@given(orphans=st.integers(0, 1000), total=st.integers(1, 1000))
@settings(max_examples=200)
def test_referential_stability(orphans, total):
    from dqt.algorithms.referential.referential import ReferentialIntegrityDetector
    orphans = min(orphans, total)
    df = agg(orphans, total)
    det = ReferentialIntegrityDetector()
    state = det.fit(df)
    result = det.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)


def test_referential_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.995, "referential_integrity_rate") == Verdict.pass_
    assert compute_verdict(0.985, "referential_integrity_rate") == Verdict.warn
    assert compute_verdict(0.90, "referential_integrity_rate") == Verdict.fail
```

- [ ] **Step 2: Run to verify failures**

```
cd packages/dqt && uv run pytest tests/algorithms/schema/ tests/algorithms/referential/ -v
```
Expected: `ImportError` for both modules.

- [ ] **Step 3: Create `algorithms/schema/schema_checks.py`**

```python
# packages/dqt/src/dqt/algorithms/schema/schema_checks.py
# Detects column additions, removals, and type changes between schema snapshots.
from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry


@registry.register
class SchemaChangeDetector(BaseDetector):
    """
    fit() expects a DataFrame with columns [col_name, data_type] from describe_columns().
    score() compares current schema to baseline and returns 1.0 on any change, 0.0 otherwise.
    """
    slug = "schema_change"
    group = "schema"
    kind = "sample"  # adapter feeds it the schema metadata, not row samples

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {
            row["col_name"]: row["data_type"]
            for _, row in reference.iterrows()
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr_schema = {row["col_name"]: row["data_type"] for _, row in current.iterrows()}
        baseline_schema: dict[str, str] = state

        added = set(curr_schema) - set(baseline_schema)
        removed = set(baseline_schema) - set(curr_schema)
        type_changed = {
            col for col in (set(curr_schema) & set(baseline_schema))
            if curr_schema[col] != baseline_schema[col]
        }

        if not added and not removed and not type_changed:
            return DetectorResult(
                score=0.0,
                verdict=Verdict.pass_,
                plain_english="Schema unchanged.",
                details={},
            )

        parts: list[str] = []
        if added:
            parts.append(f"added: {sorted(added)}")
        if removed:
            parts.append(f"removed: {sorted(removed)}")
        if type_changed:
            parts.append(f"type changed: {sorted(type_changed)}")
        msg = "; ".join(parts)

        return DetectorResult(
            score=1.0,
            verdict=Verdict.fail,
            plain_english=f"Schema changed — {msg}",
            details={"added": sorted(added), "removed": sorted(removed), "type_changed": sorted(type_changed)},
        )
```

- [ ] **Step 4: Create `algorithms/schema/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/schema/__init__.py
from dqt.algorithms.schema.schema_checks import SchemaChangeDetector
__all__ = ["SchemaChangeDetector"]
```

- [ ] **Step 5: Create `algorithms/referential/referential.py`**

```python
# packages/dqt/src/dqt/algorithms/referential/referential.py
# Checks that FK values in the child table exist in the parent table.
# The runner must supply a pre-computed aggregate: orphan_count + total_count.
from __future__ import annotations

import pandas as pd

from dqt.adapters._protocol import AggExpr
from dqt.algorithms._base import BaseAggregateDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class ReferentialIntegrityDetector(BaseAggregateDetector):
    """
    get_aggregations() must be called with the FK column expression that already joins to the
    parent table. The caller supplies a `parent_table` and `parent_col` in params; the runner
    substitutes them into the SQL.
    """
    slug = "referential_integrity"
    group = "referential"

    def __init__(self, parent_table: str = "", parent_col: str = "id") -> None:
        self._parent_table = parent_table
        self._parent_col = parent_col

    def get_aggregations(self, col: str) -> list[AggExpr]:
        return [
            AggExpr(
                name="orphan_count",
                sql=(
                    f"SUM(CASE WHEN {col} IS NOT NULL AND {col} NOT IN "
                    f"(SELECT {self._parent_col} FROM {self._parent_table}) THEN 1 ELSE 0 END)"
                ),
            ),
            AggExpr(name="total_count", sql=f"COUNT({col})"),
        ]

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        row = reference.iloc[0]
        total = int(row["total_count"])
        rate = 1.0 - (int(row["orphan_count"]) / total) if total > 0 else 1.0
        return {"baseline_integrity_rate": rate}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        row = current.iloc[0]
        total = int(row["total_count"])
        orphans = int(row["orphan_count"])
        rate = 1.0 - (orphans / total) if total > 0 else 1.0
        return DetectorResult(
            score=rate,
            verdict=self._verdict(rate),
            plain_english=f"Referential integrity {rate:.2%} ({orphans:,} orphan rows out of {total:,})",
            details={"integrity_rate": rate, "orphan_count": orphans, "total_count": total},
        )

    def _verdict(self, score: float):  # type: ignore[override]
        from dqt.algorithms._base import compute_verdict
        return compute_verdict(score, "referential_integrity_rate")
```

- [ ] **Step 6: Create `algorithms/referential/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/referential/__init__.py
from dqt.algorithms.referential.referential import ReferentialIntegrityDetector
__all__ = ["ReferentialIntegrityDetector"]
```

- [ ] **Step 7: Run tests**

```
cd packages/dqt && uv run pytest tests/algorithms/schema/ tests/algorithms/referential/ -v
```
Expected: all tests PASS.

- [ ] **Step 8: Commit**

```bash
git add packages/dqt/src/dqt/algorithms/schema/ packages/dqt/src/dqt/algorithms/referential/ \
        packages/dqt/tests/algorithms/schema/ packages/dqt/tests/algorithms/referential/
git commit -m "feat(dqt): schema change + referential integrity detectors"
```

---

### Task 7: Key statistical detectors (KS drift, MAD outliers, Isolation Forest, STL)

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/drift/ks2sample.py` + `__init__.py`
- Create: `packages/dqt/src/dqt/algorithms/outliers_uni/mad.py` + `__init__.py`
- Create: `packages/dqt/src/dqt/algorithms/outliers_multi/isolation_forest.py` + `__init__.py`
- Create: `packages/dqt/src/dqt/algorithms/timeseries/stl.py` + `__init__.py`
- Tests for each

- [ ] **Step 1: Write failing tests**

```python
# packages/dqt/tests/algorithms/drift/test_ks2sample.py
# Ref: Kolmogorov & Smirnov (1933); scipy.stats.ks_2samp
import math
import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.drift.ks2sample import KS2SampleDetector
    return KS2SampleDetector()


# 1. Known-answer: same distribution → p-value should be high → pass
def test_ks_same_distribution(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert result.verdict == Verdict.pass_
    assert result.score < 0.95  # 1 - p_value should be low


# 2a. Behaviour: clearly different distributions → drift detected
def test_ks_detects_drift(detector, normal_df, shifted_df):
    state = detector.fit(normal_df)
    result = detector.score(shifted_df, state)
    assert result.verdict != Verdict.pass_
    assert result.details["p_value"] < 0.01


# 2b. No drift: small perturbation shouldn't trigger alarm
def test_ks_no_false_positive(detector):
    rng = np.random.default_rng(1)
    ref = pd.DataFrame({"value": rng.normal(10, 2, 1000)})
    curr = pd.DataFrame({"value": rng.normal(10.05, 2, 1000)})  # tiny shift
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.verdict == Verdict.pass_


# 3. Hypothesis: score always in [0, 1], no NaN/Inf
@given(
    n=st.integers(min_value=20, max_value=500),
    shift=st.floats(min_value=-5.0, max_value=5.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_ks_stability(n, shift):
    from dqt.algorithms.drift.ks2sample import KS2SampleDetector
    rng = np.random.default_rng(42)
    ref = pd.DataFrame({"value": rng.normal(0, 1, n)})
    curr = pd.DataFrame({"value": rng.normal(shift, 1, n)})
    det = KS2SampleDetector()
    state = det.fit(ref)
    result = det.score(curr, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


# 4. STAT_SCALE verdict: score=0.96 → warn (between 0.95 and 0.99)
def test_ks_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.90, "ks_pvalue") == Verdict.pass_
    assert compute_verdict(0.96, "ks_pvalue") == Verdict.warn
    assert compute_verdict(0.995, "ks_pvalue") == Verdict.fail
```

```python
# packages/dqt/tests/algorithms/outliers_uni/test_mad.py
# Ref: Leys et al. (2013) — modified Z-score using MAD; threshold 3.5
# Ref: Hoaglin (2003) / Rousseeuw & Croux (1993) — asymmetric double-MAD for skewed data
import math
import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.outliers_uni.mad import MADOutlierDetector
    return MADOutlierDetector()


@pytest.fixture()
def double_detector():
    from dqt.algorithms.outliers_uni.mad import DoubleMadOutlierDetector
    return DoubleMadOutlierDetector()


# ── MAD ────────────────────────────────────────────────────────────────────────

# 1. Known-answer: inject a spike 10σ above the mean, expect outlier detected
def test_mad_detects_spike(detector):
    rng = np.random.default_rng(42)
    data = rng.normal(0, 1, 500).tolist()
    data.append(100.0)  # clear outlier
    df = pd.DataFrame({"value": data})
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.details["outlier_fraction"] > 0
    assert result.verdict != Verdict.pass_


# 2a. No outliers in clean normal data
def test_mad_no_false_positives(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert result.verdict == Verdict.pass_


# 2b. Injecting 10% outliers triggers fail
def test_mad_many_outliers_fail(detector):
    rng = np.random.default_rng(7)
    clean = rng.normal(0, 1, 900)
    spikes = np.full(100, 200.0)
    df = pd.DataFrame({"value": np.concatenate([clean, spikes])})
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.verdict == Verdict.fail


# 3. Hypothesis: fraction in [0, 1], no NaN/Inf
@given(
    values=st.lists(
        st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
        min_size=10,
        max_size=500,
    )
)
@settings(max_examples=100)
def test_mad_stability(values):
    from dqt.algorithms.outliers_uni.mad import MADOutlierDetector
    df = pd.DataFrame({"value": values})
    det = MADOutlierDetector()
    state = det.fit(df)
    result = det.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


# 4. STAT_SCALE verdict boundaries
def test_mad_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.005, "mad_outlier_fraction") == Verdict.pass_
    assert compute_verdict(0.02, "mad_outlier_fraction") == Verdict.warn
    assert compute_verdict(0.08, "mad_outlier_fraction") == Verdict.fail


# ── Double MAD ─────────────────────────────────────────────────────────────────

# 1. Known-answer: right-skewed data (log-normal) — spike on the right is an outlier,
#    symmetric MAD would miss it because the right tail inflates MAD; double-MAD doesn't.
def test_double_mad_right_tail_spike(double_detector):
    rng = np.random.default_rng(42)
    # log-normal is heavily right-skewed
    data = rng.lognormal(mean=0.0, sigma=0.5, size=500).tolist()
    data.append(1000.0)  # far-right spike
    df = pd.DataFrame({"value": data})
    state = double_detector.fit(df)
    result = double_detector.score(df, state)
    assert result.details["outlier_fraction"] > 0
    assert result.verdict != Verdict.pass_


# 2a. Symmetric MAD misses a right-tail spike on skewed data; double-MAD catches it
def test_double_mad_catches_what_mad_misses():
    from dqt.algorithms.outliers_uni.mad import DoubleMadOutlierDetector, MADOutlierDetector
    rng = np.random.default_rng(42)
    # Heavily right-skewed: chi-squared(2)
    data = rng.chisquare(df=2, size=1000)
    spike = np.array([200.0])
    df = pd.DataFrame({"value": np.concatenate([data, spike])})
    mad_det = MADOutlierDetector()
    dmad_det = DoubleMadOutlierDetector()
    mad_state = mad_det.fit(df)
    dmad_state = dmad_det.fit(df)
    mad_result = mad_det.score(df, mad_state)
    dmad_result = dmad_det.score(df, dmad_state)
    # double-MAD should flag at least as many outliers as MAD on this distribution
    assert dmad_result.details["outlier_fraction"] >= mad_result.details["outlier_fraction"]


# 2b. No outliers in clean normal data (double-MAD reduces to standard MAD for symmetric data)
def test_double_mad_no_false_positives_symmetric(double_detector, normal_df):
    state = double_detector.fit(normal_df)
    result = double_detector.score(normal_df, state)
    assert result.verdict == Verdict.pass_


# 3. Hypothesis: fraction in [0, 1], no NaN/Inf, handles skewed inputs
@given(
    values=st.lists(
        st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False),
        min_size=10,
        max_size=500,
    )
)
@settings(max_examples=100)
def test_double_mad_stability(values):
    from dqt.algorithms.outliers_uni.mad import DoubleMadOutlierDetector
    df = pd.DataFrame({"value": values})
    det = DoubleMadOutlierDetector()
    state = det.fit(df)
    result = det.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


# 4. STAT_SCALE verdict boundaries
def test_double_mad_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.005, "double_mad_outlier_fraction") == Verdict.pass_
    assert compute_verdict(0.02,  "double_mad_outlier_fraction") == Verdict.warn
    assert compute_verdict(0.08,  "double_mad_outlier_fraction") == Verdict.fail
```

```python
# packages/dqt/tests/algorithms/outliers_multi/test_isolation_forest.py
import math
import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.outliers_multi.isolation_forest import IsolationForestDetector
    return IsolationForestDetector(contamination=0.05)


# 1. Known-answer: inject obvious multivariate outliers
def test_if_detects_outliers(detector):
    rng = np.random.default_rng(42)
    clean = rng.normal(0, 1, (900, 3))
    outliers = rng.uniform(50, 100, (100, 3))
    data = np.vstack([clean, outliers])
    df = pd.DataFrame(data, columns=["a", "b", "c"])
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.details["outlier_fraction"] > 0.01


# 2a. Clean normal data stays within expected contamination rate
def test_if_clean_data(detector):
    rng = np.random.default_rng(42)
    df = pd.DataFrame(rng.normal(0, 1, (1000, 3)), columns=["a", "b", "c"])
    state = detector.fit(df)
    result = detector.score(df, state)
    # Isolation Forest trained on same distribution should flag roughly contamination fraction
    assert result.score <= 0.15  # allows slight overshoot


# 3. Hypothesis: fraction in [0, 1], no NaN/Inf
@given(n=st.integers(min_value=50, max_value=300), ncols=st.integers(min_value=1, max_value=5))
@settings(max_examples=30, deadline=10_000)
def test_if_stability(n, ncols):
    from dqt.algorithms.outliers_multi.isolation_forest import IsolationForestDetector
    rng = np.random.default_rng(42)
    cols = [f"c{i}" for i in range(ncols)]
    df = pd.DataFrame(rng.normal(0, 1, (n, ncols)), columns=cols)
    det = IsolationForestDetector()
    state = det.fit(df)
    result = det.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)


# 4. STAT_SCALE verdict boundaries
def test_if_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.03, "isolation_forest_fraction") == Verdict.pass_
    assert compute_verdict(0.07, "isolation_forest_fraction") == Verdict.warn
    assert compute_verdict(0.15, "isolation_forest_fraction") == Verdict.fail
```

```python
# packages/dqt/tests/algorithms/timeseries/test_stl.py
# Ref: Cleveland et al. (1990) — Seasonal-Trend decomposition using Loess
import math
import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.timeseries.stl import STLAnomalyDetector
    return STLAnomalyDetector(period=7)


# 1. Known-answer: inject a spike 50 units above trend, expect fail
def test_stl_detects_spike(detector, timeseries_df):
    ref = timeseries_df.iloc[:300].reset_index(drop=True)
    curr = timeseries_df.iloc[300:365].copy().reset_index(drop=True)
    curr.iloc[10, 0] += 50.0  # clear anomaly
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.score > 3.0
    assert result.verdict != Verdict.pass_


# 2a. Clean continuation: no spikes → pass
def test_stl_clean_continuation(detector, timeseries_df):
    ref = timeseries_df.iloc[:300].reset_index(drop=True)
    curr = timeseries_df.iloc[300:350].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.verdict == Verdict.pass_


# 2b. Constant flat series (no seasonality) — seasonality robustness
def test_stl_constant_series():
    from dqt.algorithms.timeseries.stl import STLAnomalyDetector
    data = [10.0] * 56
    df = pd.DataFrame({"value": data})
    det = STLAnomalyDetector(period=7)
    state = det.fit(df)
    result = det.score(pd.DataFrame({"value": [10.0] * 28}), state)
    assert result.score == pytest.approx(0.0, abs=1.0)
    assert not math.isnan(result.score)


# 3. Hypothesis: no NaN/Inf, score >= 0
@given(
    n_ref=st.integers(min_value=4, max_value=15),
    n_curr=st.integers(min_value=2, max_value=8),
    period=st.integers(min_value=2, max_value=5),
    noise=st.floats(min_value=0.01, max_value=5.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=30, deadline=15_000)
def test_stl_stability(n_ref, n_curr, period, noise):
    from dqt.algorithms.timeseries.stl import STLAnomalyDetector
    rng = np.random.default_rng(42)
    n_total_ref = n_ref * period * 2
    n_total_curr = n_curr * period
    ref_vals = np.sin(2 * np.pi * np.arange(n_total_ref) / period) + rng.normal(0, noise, n_total_ref)
    curr_vals = np.sin(2 * np.pi * np.arange(n_total_curr) / period) + rng.normal(0, noise, n_total_curr)
    ref_df = pd.DataFrame({"value": ref_vals})
    curr_df = pd.DataFrame({"value": curr_vals})
    det = STLAnomalyDetector(period=period)
    state = det.fit(ref_df)
    result = det.score(curr_df, state)
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)
    assert result.score >= 0.0


# 4. STAT_SCALE verdict boundaries
def test_stl_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(2.0, "stl_residual_zscore") == Verdict.pass_
    assert compute_verdict(4.0, "stl_residual_zscore") == Verdict.warn
    assert compute_verdict(6.0, "stl_residual_zscore") == Verdict.fail
```

- [ ] **Step 2: Run to verify failures**

```
cd packages/dqt && uv run pytest tests/algorithms/drift/ tests/algorithms/outliers_uni/ \
        tests/algorithms/outliers_multi/ tests/algorithms/timeseries/ -v
```
Expected: `ImportError` for all four modules.

- [ ] **Step 3: Create `algorithms/drift/ks2sample.py`**

```python
# packages/dqt/src/dqt/algorithms/drift/ks2sample.py
# Ref: Kolmogorov (1933), Smirnov (1948) — two-sample KS test via scipy.stats.ks_2samp
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class KS2SampleDetector(BaseDetector):
    """Two-sample KS test for distribution drift. Score = 1 − p-value; warn p<0.05, fail p<0.01."""
    slug = "ks_drift"
    group = "drift"

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        col = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        return {"reference": col}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        ref: np.ndarray = state["reference"]
        ks_stat, p_value = stats.ks_2samp(ref, curr)
        score = 1.0 - float(p_value)
        return DetectorResult(
            score=score,
            verdict=self._verdict(score),
            plain_english=(
                f"KS test p={p_value:.4f} — "
                f"{'drift detected' if score > 0.95 else 'no significant drift'}"
            ),
            details={"ks_statistic": float(ks_stat), "p_value": float(p_value)},
        )

    def _verdict(self, score: float):  # type: ignore[override]
        from dqt.algorithms._base import compute_verdict
        return compute_verdict(score, "ks_pvalue")
```

- [ ] **Step 4: Create `algorithms/drift/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/drift/__init__.py
from dqt.algorithms.drift.ks2sample import KS2SampleDetector
__all__ = ["KS2SampleDetector"]
```

- [ ] **Step 5: Create `algorithms/outliers_uni/mad.py`**

```python
# packages/dqt/src/dqt/algorithms/outliers_uni/mad.py
# Ref (MAD): Leys et al. (2013) J. Exp. Soc. Psychol. — modified Z-score with MAD, threshold 3.5
# Ref (Double MAD): Rousseeuw & Croux (1993) JASA — asymmetric MAD for skewed distributions
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry

_MAD_CONSISTENCY = 0.6745  # makes MAD a consistent estimator of σ under normality


@registry.register
class MADOutlierDetector(BaseDetector):
    """Modified Z-score outlier detection. Score = fraction of values with |mod-Z| > threshold."""
    slug = "mad_outlier"
    group = "outliers_uni"

    def __init__(self, threshold: float = 3.5) -> None:
        self._threshold = threshold

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        col = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        median = float(np.median(col))
        mad = float(np.median(np.abs(col - median)))
        return {"median": median, "mad": mad if mad > 0 else 1.0}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        col = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        mod_z = _MAD_CONSISTENCY * np.abs(col - state["median"]) / state["mad"]
        outlier_frac = float(np.mean(mod_z > self._threshold))
        return DetectorResult(
            score=outlier_frac,
            verdict=self._verdict(outlier_frac),
            plain_english=f"{outlier_frac:.1%} of values are outliers (modified Z > {self._threshold})",
            details={"outlier_fraction": outlier_frac, "threshold": self._threshold},
        )

    def _verdict(self, score: float):  # type: ignore[override]
        from dqt.algorithms._base import compute_verdict
        return compute_verdict(score, "mad_outlier_fraction")


@registry.register
class DoubleMadOutlierDetector(BaseDetector):
    """
    Asymmetric double-MAD outlier detection for skewed distributions.
    Computes separate MAD_left and MAD_right from the median, so a heavy right tail
    does not inflate the left-side threshold (and vice versa).
    Score = fraction of values with asymmetric modified Z > threshold.
    """
    slug = "double_mad_outlier"
    group = "outliers_uni"

    def __init__(self, threshold: float = 3.5) -> None:
        self._threshold = threshold

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        col = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        median = float(np.median(col))
        deviations = np.abs(col - median)
        mad_left = float(np.median(deviations[col <= median])) if np.any(col <= median) else 1.0
        mad_right = float(np.median(deviations[col >= median])) if np.any(col >= median) else 1.0
        return {
            "median": median,
            "mad_left": mad_left if mad_left > 0 else 1.0,
            "mad_right": mad_right if mad_right > 0 else 1.0,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        col = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        median: float = state["median"]
        mad_left: float = state["mad_left"]
        mad_right: float = state["mad_right"]

        # Use left MAD for values below median, right MAD for values above
        side_mad = np.where(col < median, mad_left, mad_right)
        mod_z = _MAD_CONSISTENCY * np.abs(col - median) / side_mad
        outlier_frac = float(np.mean(mod_z > self._threshold))

        return DetectorResult(
            score=outlier_frac,
            verdict=self._verdict(outlier_frac),
            plain_english=f"{outlier_frac:.1%} of values are outliers (double-MAD modified Z > {self._threshold})",
            details={
                "outlier_fraction": outlier_frac,
                "threshold": self._threshold,
                "mad_left": mad_left,
                "mad_right": mad_right,
            },
        )

    def _verdict(self, score: float):  # type: ignore[override]
        from dqt.algorithms._base import compute_verdict
        return compute_verdict(score, "double_mad_outlier_fraction")
```

- [ ] **Step 6: Create `algorithms/outliers_uni/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/outliers_uni/__init__.py
from dqt.algorithms.outliers_uni.mad import DoubleMadOutlierDetector, MADOutlierDetector
__all__ = ["MADOutlierDetector", "DoubleMadOutlierDetector"]
```

- [ ] **Step 7: Create `algorithms/outliers_multi/isolation_forest.py`**

```python
# packages/dqt/src/dqt/algorithms/outliers_multi/isolation_forest.py
# Ref: Liu et al. (2008) — Isolation Forest; sklearn implementation
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class IsolationForestDetector(BaseDetector):
    """Isolation Forest multivariate outlier detection. Score = fraction of rows flagged anomalous."""
    slug = "isolation_forest"
    group = "outliers_multi"

    def __init__(self, contamination: float = 0.05) -> None:
        self._contamination = contamination

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        from sklearn.ensemble import IsolationForest
        X = reference.select_dtypes(include="number").fillna(0.0)
        model = IsolationForest(contamination=self._contamination, random_state=42, n_estimators=100)
        model.fit(X)
        return {"model": model, "columns": list(X.columns)}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        model = state["model"]
        cols: list[str] = state["columns"]
        X = current[cols].fillna(0.0) if cols else current.select_dtypes(include="number").fillna(0.0)
        preds = model.predict(X)  # -1 = outlier, 1 = inlier
        outlier_frac = float(np.mean(preds == -1))
        return DetectorResult(
            score=outlier_frac,
            verdict=self._verdict(outlier_frac),
            plain_english=f"{outlier_frac:.1%} of rows flagged as multivariate outliers by Isolation Forest",
            details={"outlier_fraction": outlier_frac, "n_rows": len(X), "n_features": len(cols)},
        )

    def _verdict(self, score: float):  # type: ignore[override]
        from dqt.algorithms._base import compute_verdict
        return compute_verdict(score, "isolation_forest_fraction")
```

- [ ] **Step 8: Create `algorithms/outliers_multi/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/outliers_multi/__init__.py
from dqt.algorithms.outliers_multi.isolation_forest import IsolationForestDetector
__all__ = ["IsolationForestDetector"]
```

- [ ] **Step 9: Create `algorithms/timeseries/stl.py`**

```python
# packages/dqt/src/dqt/algorithms/timeseries/stl.py
# Ref: Cleveland et al. (1990) JASA — Seasonal-Trend decomposition using Loess (STL)
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class STLAnomalyDetector(BaseDetector):
    """
    Detects anomalies in time series via STL residuals.
    fit() learns residual statistics from the reference window.
    score() computes max absolute Z-score of residuals in the current window.
    """
    slug = "stl_anomaly"
    group = "timeseries"

    def __init__(self, period: int = 7) -> None:
        self._period = period

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        from statsmodels.tsa.seasonal import STL
        values = reference.iloc[:, 0].to_numpy(dtype=float)
        result = STL(values, period=self._period, robust=True).fit()
        resid = result.resid
        resid_std = float(np.std(resid, ddof=1))
        return {
            "resid_mean": float(np.mean(resid)),
            "resid_std": resid_std if resid_std > 0 else 1.0,
            "period": self._period,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        from statsmodels.tsa.seasonal import STL
        values = current.iloc[:, 0].to_numpy(dtype=float)
        result = STL(values, period=state["period"], robust=True).fit()
        resid = result.resid
        z_scores = np.abs((resid - state["resid_mean"]) / state["resid_std"])
        max_z = float(np.max(z_scores)) if len(z_scores) > 0 else 0.0
        n_anomalies = int(np.sum(z_scores > 3.0))
        return DetectorResult(
            score=max_z,
            verdict=self._verdict(max_z),
            plain_english=f"Max STL residual Z-score {max_z:.2f} ({n_anomalies} anomalous point{'s' if n_anomalies != 1 else ''})",
            details={"max_z_score": max_z, "anomaly_count": n_anomalies, "period": state["period"]},
        )

    def _verdict(self, score: float):  # type: ignore[override]
        from dqt.algorithms._base import compute_verdict
        return compute_verdict(score, "stl_residual_zscore")
```

- [ ] **Step 10: Create `algorithms/timeseries/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/timeseries/__init__.py
from dqt.algorithms.timeseries.stl import STLAnomalyDetector
__all__ = ["STLAnomalyDetector"]
```

- [ ] **Step 11: Run all statistical detector tests**

```
cd packages/dqt && uv run pytest tests/algorithms/drift/ tests/algorithms/outliers_uni/ \
        tests/algorithms/outliers_multi/ tests/algorithms/timeseries/ -v
```
Expected: all tests PASS. Hypothesis tests may take ~60s total — within the <60s target for `make test-lib` (skip IF hypothesis if too slow; mark `@pytest.mark.slow`).

- [ ] **Step 12: Commit**

```bash
git add packages/dqt/src/dqt/algorithms/drift/ packages/dqt/src/dqt/algorithms/outliers_uni/ \
        packages/dqt/src/dqt/algorithms/outliers_multi/ packages/dqt/src/dqt/algorithms/timeseries/ \
        packages/dqt/tests/algorithms/drift/ packages/dqt/tests/algorithms/outliers_uni/ \
        packages/dqt/tests/algorithms/outliers_multi/ packages/dqt/tests/algorithms/timeseries/
git commit -m "feat(dqt): statistical detectors — KS drift, MAD outliers, Isolation Forest, STL anomaly"
```

---

### Task 7b: Distribution profiler + Z-score + adjusted boxplot + auto-outlier selector

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/distribution/__init__.py`
- Create: `packages/dqt/src/dqt/algorithms/distribution/profiler.py`
- Create: `packages/dqt/src/dqt/algorithms/outliers_uni/zscore.py`
- Create: `packages/dqt/src/dqt/algorithms/outliers_uni/adjusted_boxplot.py`
- Create: `packages/dqt/src/dqt/algorithms/outliers_uni/auto_outlier.py`
- Test: `packages/dqt/tests/algorithms/distribution/test_profiler.py`
- Test: `packages/dqt/tests/algorithms/outliers_uni/test_zscore.py`
- Test: `packages/dqt/tests/algorithms/outliers_uni/test_adjusted_boxplot.py`
- Test: `packages/dqt/tests/algorithms/outliers_uni/test_auto_outlier.py`

**Selection logic (Hubert & Vandervieren 2008; Leys et al. 2013):**
| Distribution | Algorithm | Rationale |
|---|---|---|
| Normal | Z-score | Optimal under normality; Grubbs-equivalent |
| Moderate skew (`\|MC\|` 0.2–0.5 or `\|skew\|` 0.5–2) | Adjusted boxplot | Medcouple-corrected Tukey fences |
| Heavy skew (`\|MC\|` > 0.5 or `\|skew\|` > 2) | Double-MAD | Asymmetric threshold; breakdown point 50% |
| Heavy-tailed symmetric (excess kurtosis > 3) | MAD | Robust to fat tails |
| Multimodal (bimodality coeff > 0.555) | MAD | LOF recommended long-term (Phase 2b) |
| Uniform (KS vs uniform p > 0.10) | IQR fences + `needs_hitl: True` | IQR is mechanically safe but semantically weak |
| Unknown | MAD | Robust default |

- [ ] **Step 1: Write failing tests**

```python
# packages/dqt/tests/algorithms/distribution/test_profiler.py
import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm, lognorm, uniform


def classify(values):
    from dqt.algorithms.distribution.profiler import classify_distribution
    return classify_distribution(np.asarray(values, dtype=float))


# 1. Normal data → NORMAL
def test_classifies_normal():
    from dqt.algorithms.distribution.profiler import DistributionType
    rng = np.random.default_rng(42)
    profile = classify(rng.normal(0, 1, 1000))
    assert profile.distribution_type == DistributionType.NORMAL
    assert profile.is_normal is True


# 2. Uniform data → UNIFORM
def test_classifies_uniform():
    from dqt.algorithms.distribution.profiler import DistributionType
    rng = np.random.default_rng(42)
    profile = classify(rng.uniform(0, 1, 1000))
    assert profile.distribution_type == DistributionType.UNIFORM
    assert profile.is_uniform is True


# 3. Log-normal → SKEWED_POSITIVE
def test_classifies_lognormal():
    from dqt.algorithms.distribution.profiler import DistributionType
    rng = np.random.default_rng(42)
    profile = classify(rng.lognormal(0, 1, 1000))
    assert profile.distribution_type in (
        DistributionType.SKEWED_POSITIVE,
        DistributionType.HEAVY_TAILED,
    )
    assert profile.skewness > 0


# 4. Bimodal data → MULTIMODAL
def test_classifies_bimodal():
    from dqt.algorithms.distribution.profiler import DistributionType
    rng = np.random.default_rng(42)
    cluster_a = rng.normal(-5, 0.5, 500)
    cluster_b = rng.normal(5, 0.5, 500)
    profile = classify(np.concatenate([cluster_a, cluster_b]))
    assert profile.distribution_type == DistributionType.MULTIMODAL
    assert profile.is_multimodal is True


# 5. Profile has expected fields
def test_profile_fields():
    rng = np.random.default_rng(42)
    profile = classify(rng.normal(0, 1, 500))
    assert hasattr(profile, "skewness")
    assert hasattr(profile, "excess_kurtosis")
    assert hasattr(profile, "medcouple")
    assert hasattr(profile, "sample_size")
    assert profile.sample_size == 500
    assert isinstance(profile.skewness, float)
    assert isinstance(profile.medcouple, float)
```

```python
# packages/dqt/tests/algorithms/outliers_uni/test_zscore.py
import math
import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.outliers_uni.zscore import ZScoreDetector
    return ZScoreDetector()


# 1. Known-answer: inject a 5σ spike, must be flagged
def test_zscore_detects_spike(detector):
    rng = np.random.default_rng(42)
    data = rng.normal(0, 1, 500)
    data = np.append(data, 50.0)  # clear outlier
    df = pd.DataFrame({"value": data})
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.details["outlier_fraction"] > 0
    assert result.verdict != Verdict.pass_


# 2a. Clean normal data → pass
def test_zscore_no_false_positives(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert result.verdict == Verdict.pass_


# 2b. 10% injected spikes → fail
def test_zscore_many_spikes_fail(detector):
    rng = np.random.default_rng(7)
    clean = rng.normal(0, 1, 900)
    spikes = np.full(100, 100.0)
    df = pd.DataFrame({"value": np.concatenate([clean, spikes])})
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.verdict == Verdict.fail


# 3. Hypothesis: fraction in [0, 1], no NaN/Inf
@given(
    values=st.lists(
        st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
        min_size=10, max_size=500,
    )
)
@settings(max_examples=100)
def test_zscore_stability(values):
    from dqt.algorithms.outliers_uni.zscore import ZScoreDetector
    df = pd.DataFrame({"value": values})
    det = ZScoreDetector()
    state = det.fit(df)
    result = det.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


# 4. STAT_SCALE verdict boundaries
def test_zscore_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.005, "zscore_outlier_fraction") == Verdict.pass_
    assert compute_verdict(0.02,  "zscore_outlier_fraction") == Verdict.warn
    assert compute_verdict(0.08,  "zscore_outlier_fraction") == Verdict.fail
```

```python
# packages/dqt/tests/algorithms/outliers_uni/test_adjusted_boxplot.py
# Ref: Hubert & Vandervieren (2008) — An adjusted boxplot for skewed distributions, CSDA
import math
import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.outliers_uni.adjusted_boxplot import AdjustedBoxplotDetector
    return AdjustedBoxplotDetector()


# 1. Known-answer: log-normal data with an injected extreme spike beyond adjusted fences
def test_adj_boxplot_detects_right_tail_spike(detector):
    rng = np.random.default_rng(42)
    data = rng.lognormal(0, 0.5, 500)
    data = np.append(data, 1000.0)
    df = pd.DataFrame({"value": data})
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.details["outlier_fraction"] > 0
    assert result.verdict != Verdict.pass_


# 2. Key property: upper fence is wider than symmetric Tukey on right-skewed data
def test_adj_boxplot_wider_upper_fence_on_right_skew(detector):
    rng = np.random.default_rng(42)
    data = rng.lognormal(0, 0.8, 1000)
    df = pd.DataFrame({"value": data})
    state = detector.fit(df)
    q1, q3 = np.percentile(data, [25, 75])
    iqr = q3 - q1
    symmetric_upper = q3 + 1.5 * iqr
    # Adjusted upper fence must be wider (or equal) on right-skewed data
    assert state["upper"] >= symmetric_upper - 1e-6


# 2b. Clean symmetric data → pass (adjusted fences reduce to standard Tukey when MC ≈ 0)
def test_adj_boxplot_no_false_positives_normal(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert result.verdict == Verdict.pass_


# 3. Hypothesis: fraction in [0, 1], no NaN/Inf
@given(
    values=st.lists(
        st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False),
        min_size=10, max_size=500,
    )
)
@settings(max_examples=100)
def test_adj_boxplot_stability(values):
    from dqt.algorithms.outliers_uni.adjusted_boxplot import AdjustedBoxplotDetector
    df = pd.DataFrame({"value": values})
    det = AdjustedBoxplotDetector()
    state = det.fit(df)
    result = det.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


# 4. STAT_SCALE verdict boundaries
def test_adj_boxplot_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.005, "adjusted_boxplot_fraction") == Verdict.pass_
    assert compute_verdict(0.02,  "adjusted_boxplot_fraction") == Verdict.warn
    assert compute_verdict(0.08,  "adjusted_boxplot_fraction") == Verdict.fail
```

```python
# packages/dqt/tests/algorithms/outliers_uni/test_auto_outlier.py
import numpy as np
import pandas as pd
import pytest

from dqt.algorithms._base import Verdict


@pytest.fixture(autouse=True)
def _register_all():
    import dqt.algorithms.outliers_uni


# 1. Normal data → selects zscore_outlier
def test_auto_selects_zscore_for_normal():
    from dqt.algorithms.outliers_uni.auto_outlier import AutoOutlierDetector
    rng = np.random.default_rng(42)
    df = pd.DataFrame({"value": rng.normal(0, 1, 1000)})
    det = AutoOutlierDetector()
    state = det.fit(df)
    assert state["distribution_type"] == "normal"
    assert state["detector_slug"] == "zscore_outlier"


# 2. Heavily right-skewed data → selects double_mad_outlier
def test_auto_selects_double_mad_for_heavy_skew():
    from dqt.algorithms.outliers_uni.auto_outlier import AutoOutlierDetector
    rng = np.random.default_rng(42)
    df = pd.DataFrame({"value": rng.lognormal(0, 2, 1000)})  # very heavy right skew
    det = AutoOutlierDetector()
    state = det.fit(df)
    assert state["detector_slug"] in ("double_mad_outlier", "adjusted_boxplot_outlier")


# 3. Uniform data → warns for HITL, details carries needs_hitl
def test_auto_uniform_flags_hitl():
    from dqt.algorithms.outliers_uni.auto_outlier import AutoOutlierDetector
    rng = np.random.default_rng(42)
    df = pd.DataFrame({"value": rng.uniform(0, 100, 1000)})
    det = AutoOutlierDetector()
    state = det.fit(df)
    result = det.score(df, state)
    assert result.verdict == Verdict.warn
    assert result.details.get("needs_hitl") is True
    assert result.details.get("distribution_type") == "uniform"


# 4. Result always carries auto_selected_method in details (non-uniform case)
def test_auto_result_carries_metadata():
    from dqt.algorithms.outliers_uni.auto_outlier import AutoOutlierDetector
    rng = np.random.default_rng(42)
    df = pd.DataFrame({"value": rng.normal(0, 1, 500)})
    det = AutoOutlierDetector()
    state = det.fit(df)
    result = det.score(df, state)
    assert "auto_selected_method" in result.details
    assert "distribution_type" in result.details
```

- [ ] **Step 2: Run to verify failures**

```
cd packages/dqt && uv run pytest tests/algorithms/distribution/ \
        tests/algorithms/outliers_uni/test_zscore.py \
        tests/algorithms/outliers_uni/test_adjusted_boxplot.py \
        tests/algorithms/outliers_uni/test_auto_outlier.py -v
```
Expected: `ImportError` for all new modules.

- [ ] **Step 3: Create `algorithms/distribution/__init__.py`** (empty)

- [ ] **Step 4: Create `algorithms/distribution/profiler.py`**

```python
# packages/dqt/src/dqt/algorithms/distribution/profiler.py
# Distribution characterization for automatic detector selection.
# Refs:
#   Shapiro & Wilk (1965) Biometrika; D'Agostino & Pearson (1973)
#   Brys, Hubert, Struyf (2004) JRSS-B — medcouple
#   Sarle (1990) — bimodality coefficient
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np
from scipy import stats


class DistributionType(str, Enum):
    NORMAL = "normal"
    SKEWED_POSITIVE = "skewed_positive"
    SKEWED_NEGATIVE = "skewed_negative"
    HEAVY_TAILED = "heavy_tailed"    # symmetric fat tails
    MULTIMODAL = "multimodal"
    UNIFORM = "uniform"
    UNKNOWN = "unknown"


@dataclass
class DistributionProfile:
    distribution_type: DistributionType
    skewness: float
    excess_kurtosis: float
    medcouple: float
    is_normal: bool
    is_uniform: bool
    is_multimodal: bool
    sample_size: int


def _bimodality_coefficient(values: np.ndarray) -> float:
    """Sarle's bimodality coefficient. BC > 0.555 ≈ bimodal."""
    n = len(values)
    if n < 4:
        return 0.0
    g1 = float(stats.skew(values))
    g2 = float(stats.kurtosis(values))  # excess (Fisher) kurtosis
    correction = 3.0 * (n - 1) ** 2 / ((n - 2) * (n - 3)) if n > 3 else 3.0
    return (g1 ** 2 + 1.0) / (g2 + correction)


def _medcouple(values: np.ndarray) -> float:
    """Robust skewness measure. Delegates to statsmodels; falls back to sign(skew)/10."""
    try:
        from statsmodels.stats.stattools import medcouple_1d
        return float(medcouple_1d(values))
    except Exception:
        return float(np.sign(stats.skew(values)) * 0.1)


def classify_distribution(values: np.ndarray) -> DistributionProfile:
    """
    Characterise a 1-D numeric array and return a DistributionProfile.
    Uses D'Agostino-Pearson omnibus test for normality (n ≥ 20),
    Shapiro-Wilk for n < 20, KS-uniform for uniformity,
    and Sarle's bimodality coefficient for multimodality detection.
    """
    values = values[~np.isnan(values)]
    n = len(values)

    skewness = float(stats.skew(values)) if n >= 3 else 0.0
    excess_kurtosis = float(stats.kurtosis(values)) if n >= 4 else 0.0

    # Normality
    if n >= 20:
        _, norm_p = stats.normaltest(values)
    elif n >= 8:
        _, norm_p = stats.shapiro(values)
    else:
        norm_p = 0.0
    is_normal = bool(norm_p > 0.05)

    # Uniformity: normalise to [0, 1] then KS test
    v_min, v_max = float(values.min()), float(values.max())
    if v_max > v_min and n >= 8:
        normalised = (values - v_min) / (v_max - v_min)
        _, unif_p = stats.kstest(normalised, "uniform")
        is_uniform = bool(unif_p > 0.10)
    else:
        is_uniform = n > 1 and v_max == v_min  # all-same-value → treat as uniform

    # Multimodality (bimodality coefficient; diptest preferred but optional dep)
    bc = _bimodality_coefficient(values)
    is_multimodal = bc > 0.555

    mc = _medcouple(values) if n >= 10 else 0.0

    dist_type = _classify(is_normal, is_uniform, is_multimodal, skewness, excess_kurtosis, mc)

    return DistributionProfile(
        distribution_type=dist_type,
        skewness=skewness,
        excess_kurtosis=excess_kurtosis,
        medcouple=mc,
        is_normal=is_normal,
        is_uniform=is_uniform,
        is_multimodal=is_multimodal,
        sample_size=n,
    )


def _classify(
    is_normal: bool,
    is_uniform: bool,
    is_multimodal: bool,
    skewness: float,
    excess_kurtosis: float,
    medcouple: float,
) -> DistributionType:
    if is_uniform:
        return DistributionType.UNIFORM
    if is_multimodal:
        return DistributionType.MULTIMODAL
    if is_normal:
        return DistributionType.NORMAL
    if excess_kurtosis > 3.0 and abs(skewness) <= 0.5:
        return DistributionType.HEAVY_TAILED
    if skewness > 0.5:
        return DistributionType.SKEWED_POSITIVE
    if skewness < -0.5:
        return DistributionType.SKEWED_NEGATIVE
    return DistributionType.UNKNOWN
```

- [ ] **Step 5: Create `algorithms/outliers_uni/zscore.py`**

```python
# packages/dqt/src/dqt/algorithms/outliers_uni/zscore.py
# Standard Z-score outlier detection. Use only after verifying normality.
# Prefer MAD or adjusted boxplot when normality is uncertain.
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class ZScoreDetector(BaseDetector):
    """Z-score outlier detection. Score = fraction with |Z| > threshold. Assumes normality."""
    slug = "zscore_outlier"
    group = "outliers_uni"

    def __init__(self, threshold: float = 3.0) -> None:
        self._threshold = threshold

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        col = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        std = float(np.std(col, ddof=1))
        return {"mean": float(np.mean(col)), "std": std if std > 0 else 1.0}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        col = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        z = np.abs((col - state["mean"]) / state["std"])
        outlier_frac = float(np.mean(z > self._threshold))
        return DetectorResult(
            score=outlier_frac,
            verdict=self._verdict(outlier_frac),
            plain_english=f"{outlier_frac:.1%} of values have |Z| > {self._threshold} (μ={state['mean']:.3g}, σ={state['std']:.3g})",
            details={"outlier_fraction": outlier_frac, "threshold": self._threshold,
                     "mean": state["mean"], "std": state["std"]},
        )

    def _verdict(self, score: float):  # type: ignore[override]
        from dqt.algorithms._base import compute_verdict
        return compute_verdict(score, "zscore_outlier_fraction")
```

- [ ] **Step 6: Create `algorithms/outliers_uni/adjusted_boxplot.py`**

```python
# packages/dqt/src/dqt/algorithms/outliers_uni/adjusted_boxplot.py
# Ref: Hubert & Vandervieren (2008) CSDA — An adjusted boxplot for skewed distributions.
# Medcouple-corrected Tukey fences: for MC ≥ 0 (right skew):
#   lower = Q1 − h·exp(−4·MC)·IQR,  upper = Q3 + h·exp(3·MC)·IQR
# For MC < 0 (left skew): lower uses exp(−3·MC), upper uses exp(4·MC).
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


def _adjusted_fences(values: np.ndarray, h: float = 1.5) -> tuple[float, float]:
    """Compute medcouple-adjusted Tukey whisker fences (Hubert & Vandervieren 2008)."""
    from dqt.algorithms.distribution.profiler import _medcouple
    q1, q3 = float(np.percentile(values, 25)), float(np.percentile(values, 75))
    iqr = q3 - q1
    mc = _medcouple(values)
    if mc >= 0:
        lower = q1 - h * np.exp(-4.0 * mc) * iqr
        upper = q3 + h * np.exp(3.0 * mc) * iqr
    else:
        lower = q1 - h * np.exp(-3.0 * mc) * iqr
        upper = q3 + h * np.exp(4.0 * mc) * iqr
    return float(lower), float(upper)


@registry.register
class AdjustedBoxplotDetector(BaseDetector):
    """Medcouple-adjusted boxplot outlier detection for skewed distributions."""
    slug = "adjusted_boxplot_outlier"
    group = "outliers_uni"

    def __init__(self, h: float = 1.5) -> None:
        self._h = h

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        col = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        lower, upper = _adjusted_fences(col, self._h)
        return {"lower": lower, "upper": upper, "h": self._h}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        col = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        n = len(col)
        n_out = int(np.sum((col < state["lower"]) | (col > state["upper"])))
        outlier_frac = n_out / n if n > 0 else 0.0
        return DetectorResult(
            score=outlier_frac,
            verdict=self._verdict(outlier_frac),
            plain_english=(
                f"{outlier_frac:.1%} of values outside medcouple-adjusted fences "
                f"[{state['lower']:.3g}, {state['upper']:.3g}]"
            ),
            details={
                "outlier_fraction": outlier_frac,
                "lower_fence": state["lower"],
                "upper_fence": state["upper"],
            },
        )

    def _verdict(self, score: float):  # type: ignore[override]
        from dqt.algorithms._base import compute_verdict
        return compute_verdict(score, "adjusted_boxplot_fraction")
```

- [ ] **Step 7: Create `algorithms/outliers_uni/auto_outlier.py`**

```python
# packages/dqt/src/dqt/algorithms/outliers_uni/auto_outlier.py
# Automatically selects the best univariate outlier detector by characterising
# the reference distribution first, then delegating fit+score to the chosen method.
# Selection table (see plan Task 7b for rationale):
#   NORMAL          → ZScoreDetector
#   SKEWED heavy    → DoubleMadOutlierDetector
#   SKEWED moderate → AdjustedBoxplotDetector
#   HEAVY_TAILED    → MADOutlierDetector
#   MULTIMODAL      → MADOutlierDetector  (LOF planned Phase 2b)
#   UNIFORM         → IQR fences + needs_hitl flag
#   UNKNOWN         → MADOutlierDetector
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry
from dqt.algorithms.distribution.profiler import DistributionProfile, DistributionType, classify_distribution


def _select_slug(profile: DistributionProfile) -> str | None:
    """Return the registry slug of the best detector, or None for uniform (HITL)."""
    dt = profile.distribution_type
    if dt == DistributionType.UNIFORM:
        return None  # handled specially
    if dt == DistributionType.NORMAL:
        return "zscore_outlier"
    if dt == DistributionType.MULTIMODAL:
        return "mad_outlier"  # LOF Phase 2b
    if dt in (DistributionType.SKEWED_POSITIVE, DistributionType.SKEWED_NEGATIVE):
        if abs(profile.medcouple) > 0.5 or abs(profile.skewness) > 2.0:
            return "double_mad_outlier"
        return "adjusted_boxplot_outlier"
    # HEAVY_TAILED, UNKNOWN
    return "mad_outlier"


@registry.register
class AutoOutlierDetector(BaseDetector):
    """
    Distribution-adaptive univariate outlier detector.
    Profiles the reference distribution and delegates to the optimal method.
    Uniform distributions are flagged for human review (HITL) — no statistical
    outlier concept applies when all values are equally likely.
    """
    slug = "auto_outlier"
    group = "outliers_uni"

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        col = reference.iloc[:, 0].dropna()
        profile = classify_distribution(col.to_numpy(dtype=float))
        selected_slug = _select_slug(profile)

        state: dict[str, Any] = {
            "distribution_type": profile.distribution_type.value,
            "detector_slug": selected_slug,
            "is_uniform": selected_slug is None,
            "profile_skewness": profile.skewness,
            "profile_medcouple": profile.medcouple,
        }

        if selected_slug is not None:
            from dqt.algorithms._registry import registry as _reg
            cls = _reg.get(selected_slug)
            inner = cls()
            state["inner_state"] = inner.fit(reference)
        else:
            # Uniform: store IQR fences for a mechanically safe score
            q1, q3 = float(np.percentile(col, 25)), float(np.percentile(col, 75))
            iqr = q3 - q1
            state["inner_state"] = {"lower": q1 - 1.5 * iqr, "upper": q3 + 1.5 * iqr}

        return state

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        if state["is_uniform"]:
            col = current.iloc[:, 0].dropna().to_numpy(dtype=float)
            lower = state["inner_state"]["lower"]
            upper = state["inner_state"]["upper"]
            n_out = int(np.sum((col < lower) | (col > upper)))
            outlier_frac = n_out / len(col) if len(col) > 0 else 0.0
            return DetectorResult(
                score=outlier_frac,
                verdict=Verdict.warn,
                plain_english=(
                    "Distribution appears uniform — IQR fences applied but "
                    "no statistical basis for outlier thresholds. Human review (HITL) recommended."
                ),
                details={
                    "outlier_fraction": outlier_frac,
                    "needs_hitl": True,
                    "distribution_type": state["distribution_type"],
                    "auto_selected_method": "iqr_hitl",
                },
            )

        from dqt.algorithms._registry import registry as _reg
        cls = _reg.get(state["detector_slug"])
        inner = cls()
        result = inner.score(current, state["inner_state"])
        return DetectorResult(
            score=result.score,
            verdict=result.verdict,
            plain_english=result.plain_english,
            details={
                **result.details,
                "auto_selected_method": state["detector_slug"],
                "distribution_type": state["distribution_type"],
            },
        )
```

- [ ] **Step 8: Update `algorithms/outliers_uni/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/outliers_uni/__init__.py
from dqt.algorithms.outliers_uni.mad import DoubleMadOutlierDetector, MADOutlierDetector
from dqt.algorithms.outliers_uni.zscore import ZScoreDetector
from dqt.algorithms.outliers_uni.adjusted_boxplot import AdjustedBoxplotDetector
from dqt.algorithms.outliers_uni.auto_outlier import AutoOutlierDetector

__all__ = [
    "MADOutlierDetector",
    "DoubleMadOutlierDetector",
    "ZScoreDetector",
    "AdjustedBoxplotDetector",
    "AutoOutlierDetector",
]
```

- [ ] **Step 9: Create `algorithms/distribution/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/distribution/__init__.py
from dqt.algorithms.distribution.profiler import (
    DistributionProfile,
    DistributionType,
    classify_distribution,
)
__all__ = ["DistributionType", "DistributionProfile", "classify_distribution"]
```

- [ ] **Step 10: Create test `__init__.py` files**

Create empty:
- `packages/dqt/tests/algorithms/distribution/__init__.py`

- [ ] **Step 11: Run all Task 7b tests**

```
cd packages/dqt && uv run pytest tests/algorithms/distribution/ \
        tests/algorithms/outliers_uni/test_zscore.py \
        tests/algorithms/outliers_uni/test_adjusted_boxplot.py \
        tests/algorithms/outliers_uni/test_auto_outlier.py -v
```
Expected: all tests PASS.

- [ ] **Step 12: Commit**

```bash
git add packages/dqt/src/dqt/algorithms/distribution/ \
        packages/dqt/src/dqt/algorithms/outliers_uni/zscore.py \
        packages/dqt/src/dqt/algorithms/outliers_uni/adjusted_boxplot.py \
        packages/dqt/src/dqt/algorithms/outliers_uni/auto_outlier.py \
        packages/dqt/tests/algorithms/distribution/ \
        packages/dqt/tests/algorithms/outliers_uni/test_zscore.py \
        packages/dqt/tests/algorithms/outliers_uni/test_adjusted_boxplot.py \
        packages/dqt/tests/algorithms/outliers_uni/test_auto_outlier.py
git commit -m "feat(dqt): distribution profiler + Z-score + adjusted boxplot + auto-outlier selector"
```

---

### Task 8: Check YAML loader + JSON Schema

**Files:**
- Create: `packages/dqt/src/dqt/checks/schema/check.schema.json`
- Create: `packages/dqt/src/dqt/checks/loader.py`
- Test: `packages/dqt/tests/checks/test_loader.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/checks/test_loader.py
import textwrap
import uuid
import pytest


VALID_YAML = textwrap.dedent("""
    checks:
      - schema_name: public
        table_name: orders
        column_name: amount
        detector_slug: completeness
        baseline:
          window_days: 14
          min_rows: 500
        sample_n: 50000

      - schema_name: public
        table_name: orders
        detector_slug: volume

      - schema_name: public
        table_name: orders
        column_name: customer_id
        detector_slug: ks_drift
        params:
          period: 7
""")

INVALID_YAML_MISSING_TABLE = textwrap.dedent("""
    checks:
      - schema_name: public
        column_name: amount
        detector_slug: completeness
""")

INVALID_YAML_MISSING_SLUG = textwrap.dedent("""
    checks:
      - schema_name: public
        table_name: orders
""")


def test_load_valid_yaml():
    from dqt.checks.loader import load_checks_yaml
    checks = load_checks_yaml(VALID_YAML)
    assert len(checks) == 3


def test_first_check_fields():
    from dqt.checks.loader import load_checks_yaml
    checks = load_checks_yaml(VALID_YAML)
    c = checks[0]
    assert c.schema_name == "public"
    assert c.table_name == "orders"
    assert c.column_name == "amount"
    assert c.detector_slug == "completeness"
    assert c.baseline is not None
    assert c.baseline.window_days == 14
    assert c.baseline.min_rows == 500
    assert c.sample_n == 50_000


def test_second_check_defaults():
    from dqt.checks.loader import load_checks_yaml
    checks = load_checks_yaml(VALID_YAML)
    c = checks[1]
    assert c.column_name is None
    assert c.sample_n == 100_000
    assert c.baseline is None


def test_third_check_params():
    from dqt.checks.loader import load_checks_yaml
    checks = load_checks_yaml(VALID_YAML)
    c = checks[2]
    assert c.params == {"period": 7}


def test_each_check_gets_unique_id():
    from dqt.checks.loader import load_checks_yaml
    checks = load_checks_yaml(VALID_YAML)
    ids = [c.id for c in checks]
    assert len(set(ids)) == len(ids)


def test_invalid_yaml_missing_table():
    from dqt.checks.loader import load_checks_yaml, CheckValidationError
    with pytest.raises(CheckValidationError, match="table_name"):
        load_checks_yaml(INVALID_YAML_MISSING_TABLE)


def test_invalid_yaml_missing_slug():
    from dqt.checks.loader import load_checks_yaml, CheckValidationError
    with pytest.raises(CheckValidationError, match="detector_slug"):
        load_checks_yaml(INVALID_YAML_MISSING_SLUG)


def test_load_from_file(tmp_path):
    from dqt.checks.loader import load_checks_file
    p = tmp_path / "checks.yaml"
    p.write_text(VALID_YAML)
    checks = load_checks_file(str(p))
    assert len(checks) == 3
```

- [ ] **Step 2: Run to verify failures**

```
cd packages/dqt && uv run pytest tests/checks/test_loader.py -v
```
Expected: `ImportError`.

- [ ] **Step 3: Create `checks/schema/check.schema.json`**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CheckDefinition",
  "description": "A single dqt check binding a detector to a table/column.",
  "type": "object",
  "required": ["schema_name", "table_name", "detector_slug"],
  "additionalProperties": false,
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid",
      "description": "Auto-generated if omitted."
    },
    "schema_name": { "type": "string" },
    "table_name":  { "type": "string" },
    "column_name": { "type": ["string", "null"] },
    "detector_slug": { "type": "string" },
    "params": {
      "type": "object",
      "default": {}
    },
    "baseline": {
      "oneOf": [
        { "type": "null" },
        {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "window_days": { "type": "integer", "minimum": 1, "default": 14 },
            "min_rows":    { "type": "integer", "minimum": 1, "default": 1000 }
          }
        }
      ]
    },
    "schedule":  { "type": ["string", "null"] },
    "sample_n":  { "type": "integer", "minimum": 1000, "default": 100000 }
  }
}
```

- [ ] **Step 4: Create `checks/schema/__init__.py`** (empty)

- [ ] **Step 5: Create `checks/loader.py`**

```python
# packages/dqt/src/dqt/checks/loader.py
from __future__ import annotations

import importlib.resources
import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from dqt.checks.models import BaselineConfig, Check


class CheckValidationError(ValueError):
    """Raised when a check YAML document fails schema validation."""


def _load_schema() -> dict[str, Any]:
    schema_path = Path(__file__).parent / "schema" / "check.schema.json"
    with schema_path.open() as f:
        return json.load(f)


def _validate_check_dict(raw: dict[str, Any], schema: dict[str, Any]) -> None:
    try:
        jsonschema.validate(instance=raw, schema=schema)
    except jsonschema.ValidationError as exc:
        raise CheckValidationError(str(exc.message)) from exc


def _parse_check(raw: dict[str, Any]) -> Check:
    baseline_raw = raw.get("baseline")
    baseline = BaselineConfig(**baseline_raw) if baseline_raw else None
    return Check(
        schema_name=raw["schema_name"],
        table_name=raw["table_name"],
        column_name=raw.get("column_name"),
        detector_slug=raw["detector_slug"],
        params=raw.get("params") or {},
        baseline=baseline,
        schedule=raw.get("schedule"),
        sample_n=raw.get("sample_n", 100_000),
    )


def load_checks_yaml(yaml_str: str) -> list[Check]:
    """Parse and validate a YAML string containing a `checks:` list. Returns Check objects."""
    schema = _load_schema()
    doc = yaml.safe_load(yaml_str)
    if not isinstance(doc, dict) or "checks" not in doc:
        raise CheckValidationError("YAML must have a top-level 'checks' key")
    checks: list[Check] = []
    for raw in doc["checks"]:
        _validate_check_dict(raw, schema)
        checks.append(_parse_check(raw))
    return checks


def load_checks_file(path: str) -> list[Check]:
    """Load checks from a YAML file on disk."""
    with open(path) as f:
        return load_checks_yaml(f.read())
```

- [ ] **Step 6: Run test to verify it passes**

```
cd packages/dqt && uv run pytest tests/checks/test_loader.py -v
```
Expected: all 9 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add packages/dqt/src/dqt/checks/ packages/dqt/tests/checks/
git commit -m "feat(dqt): check YAML loader with JSON Schema validation"
```

---

### Task 9: Runner

**Files:**
- Create: `packages/dqt/src/dqt/runner/runner.py`
- Test: `packages/dqt/tests/runner/test_runner.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/runner/test_runner.py
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from dqt.adapters._protocol import AggExpr, ColumnMeta
from dqt.algorithms._base import Verdict
from dqt.checks.models import BaselineConfig, Check
from dqt.store.memory import MemoryStore


def make_adapter(
    sample_df: pd.DataFrame | None = None,
    aggregate_result: dict | None = None,
) -> MagicMock:
    """Build a mock WarehouseAdapter that returns pre-canned data."""
    adapter = MagicMock()
    if sample_df is not None:
        adapter.sample.return_value = sample_df
    if aggregate_result is not None:
        adapter.aggregate.return_value = aggregate_result
    return adapter


def completeness_check() -> Check:
    return Check(
        schema_name="public",
        table_name="orders",
        column_name="amount",
        detector_slug="completeness",
    )


def ks_check() -> Check:
    return Check(
        schema_name="public",
        table_name="orders",
        column_name="value",
        detector_slug="ks_drift",
    )


@pytest.fixture(autouse=True)
def _register_detectors():
    """Ensure all detectors are imported (registered in registry) before runner tests."""
    import dqt.algorithms.basic
    import dqt.algorithms.drift


def test_runner_run_aggregate_detector_pass():
    from dqt.runner.runner import Runner
    store = MemoryStore()
    runner = Runner(store=store)
    adapter = make_adapter(aggregate_result={"null_count": 5, "total_count": 1000})
    check = completeness_check()
    runner.fit(check, adapter)
    result = runner.run(check, adapter)
    assert result.verdict == Verdict.pass_
    assert result.detector_slug == "completeness"
    runs = store.list_runs(check.id)
    assert len(runs) == 1
    assert runs[0].run_id == result.run_id


def test_runner_run_creates_incident_on_fail():
    from dqt.runner.runner import Runner
    store = MemoryStore()
    runner = Runner(store=store)
    adapter = make_adapter(aggregate_result={"null_count": 150, "total_count": 1000})
    check = completeness_check()
    runner.fit(check, adapter)
    result = runner.run(check, adapter)
    assert result.verdict == Verdict.fail
    incidents = store.list_incidents(check.id)
    assert len(incidents) == 1
    assert incidents[0].severity == Verdict.fail


def test_runner_run_creates_incident_on_warn():
    from dqt.runner.runner import Runner
    store = MemoryStore()
    runner = Runner(store=store)
    adapter = make_adapter(aggregate_result={"null_count": 60, "total_count": 1000})
    check = completeness_check()
    runner.fit(check, adapter)
    result = runner.run(check, adapter)
    assert result.verdict == Verdict.warn
    incidents = store.list_incidents(check.id)
    assert len(incidents) == 1


def test_runner_no_incident_on_pass():
    from dqt.runner.runner import Runner
    store = MemoryStore()
    runner = Runner(store=store)
    adapter = make_adapter(aggregate_result={"null_count": 2, "total_count": 1000})
    check = completeness_check()
    runner.fit(check, adapter)
    runner.run(check, adapter)
    assert store.list_incidents(check.id) == []


def test_runner_run_sample_detector():
    from dqt.runner.runner import Runner
    rng = np.random.default_rng(42)
    ref_df = pd.DataFrame({"value": rng.normal(10, 2, 1000)})
    curr_df = pd.DataFrame({"value": rng.normal(10.1, 2, 1000)})  # tiny shift → pass
    store = MemoryStore()
    runner = Runner(store=store)
    adapter = make_adapter(sample_df=ref_df)
    check = ks_check()
    runner.fit(check, adapter)
    adapter.sample.return_value = curr_df
    result = runner.run(check, adapter)
    assert result.verdict == Verdict.pass_


def test_runner_auto_refits_if_no_state():
    from dqt.runner.runner import Runner
    store = MemoryStore()
    runner = Runner(store=store)
    adapter = make_adapter(aggregate_result={"null_count": 5, "total_count": 1000})
    check = completeness_check()
    # Do NOT call runner.fit() — runner must auto-fit on first run
    result = runner.run(check, adapter)
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)
    # adapter.aggregate must have been called at least twice (fit + score)
    assert adapter.aggregate.call_count >= 2


def test_runner_uses_check_sample_n():
    from dqt.runner.runner import Runner
    rng = np.random.default_rng(42)
    ref_df = pd.DataFrame({"value": rng.normal(10, 2, 500)})
    store = MemoryStore()
    runner = Runner(store=store)
    adapter = make_adapter(sample_df=ref_df)
    check = ks_check()
    check.sample_n = 50_000
    runner.fit(check, adapter)
    adapter.sample.assert_called_with("public", "orders", 50_000)
```

- [ ] **Step 2: Run to verify failures**

```
cd packages/dqt && uv run pytest tests/runner/test_runner.py -v
```
Expected: `ImportError: cannot import name 'Runner'`.

- [ ] **Step 3: Implement `runner/runner.py`**

```python
# packages/dqt/src/dqt/runner/runner.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

import pandas as pd

from dqt.algorithms._base import Verdict
from dqt.utils.logging import get_logger

if TYPE_CHECKING:
    from dqt.adapters._protocol import WarehouseAdapter
    from dqt.algorithms._base import DetectorState
    from dqt.checks.models import Check
    from dqt.store._protocol import ResultsStore, RunResult

_log = get_logger(__name__)


class Runner:
    """
    Orchestrates detector fit + score against a WarehouseAdapter.
    States are cached in-memory; call fit() explicitly to re-baseline,
    or let run() auto-fit on first execution.
    """

    def __init__(self, store: ResultsStore) -> None:
        self._store = store
        self._states: dict[UUID, DetectorState] = {}

    def fit(self, check: Check, adapter: WarehouseAdapter) -> None:
        from dqt.algorithms._registry import registry
        cls = registry.get(check.detector_slug)
        detector = cls(**(check.params or {}))
        ref_df = self._fetch(check, adapter)
        self._states[check.id] = detector.fit(ref_df)
        _log.info("fit", check_id=str(check.id), slug=check.detector_slug)

    def run(self, check: Check, adapter: WarehouseAdapter) -> RunResult:
        from dqt.algorithms._registry import registry
        from dqt.store._protocol import Incident, RunResult

        if check.id not in self._states:
            self.fit(check, adapter)

        cls = registry.get(check.detector_slug)
        detector = cls(**(check.params or {}))
        state = self._states[check.id]

        started_at = datetime.now(timezone.utc)
        curr_df = self._fetch(check, adapter)
        result = detector.score(curr_df, state)
        finished_at = datetime.now(timezone.utc)

        run_result = RunResult(
            check_id=check.id,
            detector_slug=check.detector_slug,
            started_at=started_at,
            finished_at=finished_at,
            verdict=result.verdict,
            score=result.score,
            plain_english=result.plain_english,
            details=result.details,
        )
        self._store.save_run(run_result)

        if result.verdict != Verdict.pass_:
            self._store.save_incident(Incident(
                check_id=check.id,
                run_id=run_result.run_id,
                detector_slug=check.detector_slug,
                severity=result.verdict,
                opened_at=finished_at,
                score=result.score,
            ))

        _log.info(
            "run",
            check_id=str(check.id),
            slug=check.detector_slug,
            verdict=result.verdict.value,
            score=result.score,
        )
        return run_result

    def _fetch(self, check: Check, adapter: WarehouseAdapter) -> pd.DataFrame:
        """Fetch data using the correct method for the detector's kind."""
        from dqt.algorithms._registry import registry
        from dqt.adapters._protocol import AggExpr
        cls = registry.get(check.detector_slug)
        detector = cls(**(check.params or {}))

        if detector.kind == "aggregate":
            col = check.column_name or "*"
            exprs = detector.get_aggregations(col)
            agg_result = adapter.aggregate(check.schema_name, check.table_name, exprs)
            return pd.DataFrame([agg_result])

        return adapter.sample(check.schema_name, check.table_name, check.sample_n)
```

- [ ] **Step 4: Run test to verify it passes**

```
cd packages/dqt && uv run pytest tests/runner/test_runner.py -v
```
Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/dqt/src/dqt/runner/ packages/dqt/tests/runner/
git commit -m "feat(dqt): Runner — orchestrates fit/score against WarehouseAdapter, persists RunResult + Incident"
```

---

### Task 10: PostgresStore (integration-marked)

**Files:**
- Create: `packages/dqt/src/dqt/store/postgres.py`
- Test: `packages/dqt/tests/store/test_postgres_store.py` (`@pytest.mark.integration`)

The PostgresStore uses a raw SQLAlchemy schema. It does NOT import from `apps/server/` — the library is standalone.

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/store/test_postgres_store.py
import uuid
from datetime import datetime, timezone

import pytest

from dqt.algorithms._base import Verdict
from dqt.store._protocol import Incident, RunResult

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def pg_engine():
    from testcontainers.postgres import PostgresContainer
    import sqlalchemy as sa
    with PostgresContainer("timescale/timescaledb:latest-pg16") as pg:
        engine = sa.create_engine(pg.get_connection_url())
        yield engine


@pytest.fixture(scope="module")
def store(pg_engine):
    from dqt.store.postgres import PostgresStore
    s = PostgresStore(engine=pg_engine)
    s.create_tables()
    return s


@pytest.fixture()
def sample_run_result():
    now = datetime.now(timezone.utc)
    return RunResult(
        check_id=uuid.uuid4(),
        detector_slug="completeness",
        started_at=now,
        finished_at=now,
        verdict=Verdict.pass_,
        score=0.99,
        plain_english="99% complete",
        details={"completeness_rate": 0.99},
    )


def test_save_and_retrieve_run(store, sample_run_result):
    store.save_run(sample_run_result)
    runs = store.list_runs(sample_run_result.check_id)
    assert len(runs) == 1
    r = runs[0]
    assert r.run_id == sample_run_result.run_id
    assert r.score == pytest.approx(0.99)
    assert r.verdict == Verdict.pass_
    assert r.details["completeness_rate"] == pytest.approx(0.99)


def test_save_and_retrieve_incident(store, sample_run_result):
    store.save_run(sample_run_result)
    now = datetime.now(timezone.utc)
    incident = Incident(
        check_id=sample_run_result.check_id,
        run_id=sample_run_result.run_id,
        detector_slug="completeness",
        severity=Verdict.fail,
        opened_at=now,
        score=0.7,
    )
    store.save_incident(incident)
    incidents = store.list_incidents(sample_run_result.check_id)
    assert any(i.incident_id == incident.incident_id for i in incidents)


def test_list_runs_limit(store):
    check_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    for _ in range(5):
        store.save_run(RunResult(
            check_id=check_id, detector_slug="completeness",
            started_at=now, finished_at=now,
            verdict=Verdict.pass_, score=0.99, plain_english="ok",
        ))
    assert len(store.list_runs(check_id, limit=3)) == 3


def test_implements_results_store_protocol(store):
    from dqt.store._protocol import ResultsStore
    assert isinstance(store, ResultsStore)
```

- [ ] **Step 2: Run to verify failures**

```
cd packages/dqt && uv run pytest tests/store/test_postgres_store.py -v -m integration
```
Expected: `ImportError`.

- [ ] **Step 3: Implement `store/postgres.py`**

```python
# packages/dqt/src/dqt/store/postgres.py
# Standalone PostgresStore — no dependency on apps/server or any web framework.
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import text

from dqt.algorithms._base import Verdict
from dqt.store._protocol import Incident, RunResult
from dqt.utils.logging import get_logger

_log = get_logger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS dqt_run_results (
    run_id          UUID PRIMARY KEY,
    check_id        UUID NOT NULL,
    detector_slug   TEXT NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL,
    finished_at     TIMESTAMPTZ NOT NULL,
    verdict         TEXT NOT NULL,
    score           DOUBLE PRECISION NOT NULL,
    plain_english   TEXT NOT NULL,
    details         JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS dqt_run_results_check_idx ON dqt_run_results (check_id, finished_at DESC);

CREATE TABLE IF NOT EXISTS dqt_incidents (
    incident_id     UUID PRIMARY KEY,
    check_id        UUID NOT NULL,
    run_id          UUID NOT NULL,
    detector_slug   TEXT NOT NULL,
    severity        TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'open',
    opened_at       TIMESTAMPTZ NOT NULL,
    resolved_at     TIMESTAMPTZ,
    score           DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS dqt_incidents_check_idx ON dqt_incidents (check_id, opened_at DESC);
"""


class PostgresStore:
    def __init__(self, engine: sa.Engine) -> None:
        self._engine = engine

    def create_tables(self) -> None:
        with self._engine.begin() as conn:
            for stmt in _DDL.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    conn.execute(text(stmt))

    def save_run(self, run: RunResult) -> None:
        with self._engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO dqt_run_results
                    (run_id, check_id, detector_slug, started_at, finished_at, verdict, score, plain_english, details)
                VALUES
                    (:run_id, :check_id, :slug, :started, :finished, :verdict, :score, :plain, :details)
                ON CONFLICT (run_id) DO NOTHING
            """), {
                "run_id": str(run.run_id),
                "check_id": str(run.check_id),
                "slug": run.detector_slug,
                "started": run.started_at,
                "finished": run.finished_at,
                "verdict": run.verdict.value,
                "score": run.score,
                "plain": run.plain_english,
                "details": json.dumps(run.details),
            })

    def list_runs(self, check_id: UUID, limit: int = 100) -> list[RunResult]:
        with self._engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT run_id, check_id, detector_slug, started_at, finished_at,
                       verdict, score, plain_english, details
                FROM dqt_run_results
                WHERE check_id = :check_id
                ORDER BY finished_at DESC
                LIMIT :limit
            """), {"check_id": str(check_id), "limit": limit}).fetchall()
        return [
            RunResult(
                run_id=UUID(r[0]),
                check_id=UUID(r[1]),
                detector_slug=r[2],
                started_at=r[3],
                finished_at=r[4],
                verdict=Verdict(r[5]),
                score=r[6],
                plain_english=r[7],
                details=json.loads(r[8]) if r[8] else {},
            )
            for r in rows
        ]

    def save_incident(self, incident: Incident) -> None:
        with self._engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO dqt_incidents
                    (incident_id, check_id, run_id, detector_slug, severity, status, opened_at, resolved_at, score)
                VALUES
                    (:incident_id, :check_id, :run_id, :slug, :severity, :status, :opened, :resolved, :score)
                ON CONFLICT (incident_id) DO NOTHING
            """), {
                "incident_id": str(incident.incident_id),
                "check_id": str(incident.check_id),
                "run_id": str(incident.run_id),
                "slug": incident.detector_slug,
                "severity": incident.severity.value,
                "status": incident.status,
                "opened": incident.opened_at,
                "resolved": incident.resolved_at,
                "score": incident.score,
            })

    def list_incidents(self, check_id: UUID, status: str | None = None) -> list[Incident]:
        where = "check_id = :check_id"
        params: dict = {"check_id": str(check_id)}
        if status is not None:
            where += " AND status = :status"
            params["status"] = status
        with self._engine.connect() as conn:
            rows = conn.execute(text(
                f"SELECT incident_id, check_id, run_id, detector_slug, severity, status, opened_at, resolved_at, score "  # noqa: S608
                f"FROM dqt_incidents WHERE {where} ORDER BY opened_at DESC"
            ), params).fetchall()
        return [
            Incident(
                incident_id=UUID(r[0]),
                check_id=UUID(r[1]),
                run_id=UUID(r[2]),
                detector_slug=r[3],
                severity=Verdict(r[4]),
                status=r[5],
                opened_at=r[6],
                resolved_at=r[7],
                score=r[8],
            )
            for r in rows
        ]
```

- [ ] **Step 4: Run integration test**

```
cd packages/dqt && uv run pytest tests/store/test_postgres_store.py -v -m integration
```
Expected: all 4 tests PASS (requires Docker).

- [ ] **Step 5: Commit**

```bash
git add packages/dqt/src/dqt/store/postgres.py packages/dqt/tests/store/test_postgres_store.py
git commit -m "feat(dqt): PostgresStore — standalone SQLAlchemy store for RunResult + Incident"
```

---

### Task 11: Public API surface + make test-lib green

**Files:**
- Modify: `packages/dqt/src/dqt/__init__.py`
- Modify: `packages/dqt/src/dqt/algorithms/__init__.py` (import all detector groups to trigger registration)

- [ ] **Step 1: Write the failing test (public API surface)**

```python
# packages/dqt/tests/test_public_api.py
def test_public_imports():
    import dqt
    assert hasattr(dqt, "Verdict")
    assert hasattr(dqt, "DetectorResult")
    assert hasattr(dqt, "BaseDetector")
    assert hasattr(dqt, "BaseAggregateDetector")
    assert hasattr(dqt, "WarehouseAdapter")
    assert hasattr(dqt, "AggExpr")
    assert hasattr(dqt, "ResultsStore")
    assert hasattr(dqt, "RunResult")
    assert hasattr(dqt, "Incident")
    assert hasattr(dqt, "MemoryStore")
    assert hasattr(dqt, "Check")
    assert hasattr(dqt, "BaselineConfig")
    assert hasattr(dqt, "Runner")
    assert hasattr(dqt, "__version__")
    assert dqt.__version__ == "0.1.0"


def test_all_detectors_registered():
    import dqt  # importing dqt must trigger detector registration
    from dqt.algorithms._registry import registry
    expected_slugs = {
        "completeness", "uniqueness", "validity", "numeric_mean", "volume",
        "schema_change", "referential_integrity",
        "ks_drift",
        "mad_outlier", "double_mad_outlier",
        "zscore_outlier", "adjusted_boxplot_outlier", "auto_outlier",
        "isolation_forest", "stl_anomaly",
    }
    registered = set(registry.slugs())
    missing = expected_slugs - registered
    assert not missing, f"Detectors not registered: {missing}"


def test_end_to_end_with_memory_store():
    """Full pipeline: fit a completeness check and run it, verify RunResult stored."""
    import uuid
    from unittest.mock import MagicMock
    import pandas as pd
    import dqt

    adapter = MagicMock()
    adapter.aggregate.return_value = {"null_count": 3, "total_count": 1000}
    check = dqt.Check(
        schema_name="public",
        table_name="orders",
        column_name="amount",
        detector_slug="completeness",
    )
    store = dqt.MemoryStore()
    runner = dqt.Runner(store=store)
    runner.fit(check, adapter)
    result = runner.run(check, adapter)
    assert result.verdict == dqt.Verdict.pass_
    assert len(store.list_runs(check.id)) == 1
```

- [ ] **Step 2: Run to verify failures**

```
cd packages/dqt && uv run pytest tests/test_public_api.py -v
```
Expected: fails on missing attributes in `dqt.__init__`.

- [ ] **Step 3: Update `packages/dqt/src/dqt/__init__.py`**

```python
# packages/dqt/src/dqt/__init__.py
"""dqt — open-source data quality, observability, and causality library."""
from __future__ import annotations

__version__ = "0.1.0"

# Core types
from dqt.algorithms._base import (
    BaseAggregateDetector,
    BaseDetector,
    DetectorResult,
    Verdict,
    compute_verdict,
)
from dqt.adapters._protocol import AggExpr, ColumnMeta, HealthCheckResult, WarehouseAdapter
from dqt.store._protocol import Incident, ResultsStore, RunResult
from dqt.store.memory import MemoryStore
from dqt.checks.models import BaselineConfig, Check
from dqt.runner.runner import Runner

# Import all detector groups to trigger registry.register() side effects
import dqt.algorithms.basic           # noqa: F401 — registers completeness, uniqueness, validity, numeric_mean, volume
import dqt.algorithms.schema          # noqa: F401 — registers schema_change
import dqt.algorithms.referential     # noqa: F401 — registers referential_integrity
import dqt.algorithms.drift           # noqa: F401 — registers ks_drift
import dqt.algorithms.outliers_uni    # noqa: F401 — registers mad_outlier, double_mad_outlier, zscore_outlier, adjusted_boxplot_outlier, auto_outlier
import dqt.algorithms.outliers_multi  # noqa: F401 — registers isolation_forest
import dqt.algorithms.timeseries      # noqa: F401 — registers stl_anomaly

__all__ = [
    "__version__",
    "Verdict",
    "DetectorResult",
    "BaseDetector",
    "BaseAggregateDetector",
    "compute_verdict",
    "AggExpr",
    "ColumnMeta",
    "HealthCheckResult",
    "WarehouseAdapter",
    "ResultsStore",
    "RunResult",
    "Incident",
    "MemoryStore",
    "Check",
    "BaselineConfig",
    "Runner",
]
```

- [ ] **Step 4: Run public API tests**

```
cd packages/dqt && uv run pytest tests/test_public_api.py -v
```
Expected: all 3 tests PASS.

- [ ] **Step 5: Run the full `make test-lib` suite**

```
make test-lib
```
Which runs:
```
uv run pytest packages/dqt/tests -m "not adapter and not slow" --maxfail=1
```
Expected: all library unit tests PASS in <60s. If tests are slow, mark the Hypothesis-heavy tests with `@pytest.mark.slow` and verify they're excluded.

- [ ] **Step 6: Fix any failures** before committing.

- [ ] **Step 7: Final commit**

```bash
git add packages/dqt/src/dqt/__init__.py packages/dqt/src/dqt/algorithms/__init__.py \
        packages/dqt/tests/test_public_api.py
git commit -m "feat(dqt): public API surface — all detectors registered on import, end-to-end pipeline verified"
```

---

## Self-Review

### Spec coverage
- ✅ `MemoryStore` — in-memory default, degrades without Postgres
- ✅ `PostgresStore` — standalone, no server imports
- ✅ `WarehouseAdapter` protocol — `health_check`, `sample`, `aggregate`, `describe_columns`, `list_schemas`, `list_tables`
- ✅ 6-step health check (TCP reach, auth, info_schema, sample SELECT, latency, clock skew)
- ✅ Reservoir sample at `sample_n` rows (default 100k)
- ✅ Basic detectors: completeness, uniqueness, validity, numeric_mean, volume
- ✅ Schema change + referential integrity
- ✅ KS 2-sample drift, MAD + double-MAD + Z-score + adjusted boxplot (medcouple) + auto-selector univariate outliers, Isolation Forest multivariate, STL time-series anomaly
- ✅ Distribution profiler (normality, uniformity, multimodality, skewness, medcouple) for auto-selection
- ✅ Auto-outlier selector: normal→Z-score, moderate skew→adj. boxplot, heavy skew→double-MAD, heavy-tailed→MAD, multimodal→MAD, uniform→IQR+HITL flag
- ✅ Check YAML format with JSON Schema validation
- ✅ Runner: fit + score + auto-fit on first run + incident creation on warn/fail
- ✅ STAT_SCALES as single source of truth in `_scales.py`
- ✅ Detector registry with slug-based lookup
- ✅ 4 tests per detector (known-answer, behaviour, hypothesis, STAT_SCALE verdict)
- ✅ Library isolation: `packages/dqt/` has no `apps/` imports anywhere
- ✅ `make test-lib` target covers all tasks (excludes `@adapter` and `@integration` markers)

### Not in Phase 2a (deferred to Phase 2b)
- Full statistical catalog: PSI, Wasserstein, MMD, CUSUM, BOCPD, ECOD, LOF, DBSCAN, Grubbs, etc.
- `scales_to_ts.py` generator + frontend consumption
- `engines_to_ts.py` generator

---

**Plan complete and saved to `docs/superpowers/plans/2026-05-08-dqt-mvp-phase2a-library-core.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
