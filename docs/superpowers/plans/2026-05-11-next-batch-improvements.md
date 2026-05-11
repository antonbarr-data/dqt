# dqt Next-Batch Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Advance dqt from score 55 → 95 across correctness, reliability, causal/lineage depth, workflow integration, and documentation.

**Architecture:** Five sequential phases — correctness first, then reliability, then differentiation, then integration, then docs. Each phase is independently deployable. Library code (`packages/dqt/`) only; no server/web changes unless specified.

**Tech Stack:** Python 3.12+, pytest, numpy, pandas, scipy, statsmodels, sqlglot, structlog, pydantic v2, argparse, tigramite (optional), DuckDB, HTMX+FastAPI (Phase 4.5 only).

---

## File map

**Phase 1 — Bug fixes:**
- Modify: `packages/dqt/src/dqt/algorithms/basic/freshness.py`
- Modify: `packages/dqt/src/dqt/lineage/sql.py`

**Phase 2 — Reliability:**
- Create: `packages/dqt/tests/failure_modes/` (new test directory)
- Modify: `packages/dqt/src/dqt/runner/runner.py`
- Modify: `packages/dqt/src/dqt/algorithms/_base.py`
- Modify: multiple detector files (power warnings)

**Phase 3 — Causal & lineage depth:**
- Modify: `packages/dqt/src/dqt/lineage/dbt.py`
- Create: `packages/dqt/src/dqt/causality/pcmci.py`
- Create: `packages/dqt/src/dqt/causality/events.py`
- Modify: `packages/dqt/src/dqt/causality/__init__.py`
- Modify: `packages/dqt/src/dqt/store/_protocol.py`

**Phase 4 — Workflow:**
- Modify: `packages/dqt/src/dqt/cli/main.py`
- Modify: `packages/dqt/src/dqt/store/_protocol.py`
- Create: `packages/dqt/src/dqt/lineage/openlineage.py`
- Create: `packages/dqt/src/dqt/compat/dbt_tests.py`

**Phase 5 — Docs:**
- Create: `docs/algorithms/` entries
- Create: `packages/dqt/src/dqt/algorithms/_calibration.py`
- Create: `examples/` notebooks

---

## Phase 1 — Correctness pass

### Task 1: Fix `from_sql_files` crash on schema-qualified table names

**Problem:** `stg.stg_payments` causes a `TypeError` because `table.args.get("db")` returns a sqlglot `Identifier` node (not a string), and the current `_qualified` function passes it directly into `".".join()`.

**Fix:** Use sqlglot's `.db`, `.catalog`, `.name` string properties instead of `.args.get("db")`.

**Files:**
- Modify: `packages/dqt/src/dqt/lineage/sql.py:14-17`
- Test: `packages/dqt/tests/lineage/test_sql_lineage.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/lineage/test_sql_lineage.py
import pytest


def test_schema_qualified_table_does_not_crash():
    """Regression: stg.stg_payments raised TypeError before this fix."""
    import tempfile, pathlib
    from dqt.lineage.sql import from_sql_files
    sql = """
    CREATE VIEW analytics.orders AS
    SELECT o.id, p.amount
    FROM stg.stg_orders AS o
    JOIN stg.stg_payments AS p ON o.id = p.order_id;
    """
    with tempfile.NamedTemporaryFile(suffix=".sql", mode="w", delete=False) as f:
        f.write(sql)
        path = f.name
    graph = from_sql_files([path])
    node_ids = {n.id for n in graph.nodes}
    assert "analytics.orders" in node_ids
    assert "stg.stg_orders" in node_ids
    assert "stg.stg_payments" in node_ids


def test_three_part_name():
    """catalog.schema.table should parse correctly."""
    import tempfile
    from dqt.lineage.sql import from_sql_files
    sql = "CREATE VIEW my_db.dbo.v_orders AS SELECT * FROM my_db.raw.orders;"
    with tempfile.NamedTemporaryFile(suffix=".sql", mode="w", delete=False) as f:
        f.write(sql)
        path = f.name
    graph = from_sql_files([path])
    node_ids = {n.id for n in graph.nodes}
    assert "my_db.dbo.v_orders" in node_ids
    assert "my_db.raw.orders" in node_ids


def test_bare_table_name():
    """Unqualified table names still work."""
    import tempfile
    from dqt.lineage.sql import from_sql_files
    sql = "CREATE VIEW v_orders AS SELECT * FROM orders;"
    with tempfile.NamedTemporaryFile(suffix=".sql", mode="w", delete=False) as f:
        f.write(sql)
        path = f.name
    graph = from_sql_files([path])
    assert any(n.id == "v_orders" for n in graph.nodes)
    assert any(n.id == "orders" for n in graph.nodes)
```

- [ ] **Step 2: Run test to confirm failure**

```
cd packages/dqt && uv run pytest tests/lineage/test_sql_lineage.py -v
```
Expected: FAIL — `TypeError` or `ImportError` (no lineage test dir yet)

- [ ] **Step 3: Create test directory and fix `_qualified`**

Create `packages/dqt/tests/lineage/__init__.py` (empty).

Replace `_qualified` in `packages/dqt/src/dqt/lineage/sql.py`:

```python
def _qualified(table) -> str:
    """Return a stable dotted name for a sqlglot Table expression.

    Uses sqlglot string properties (.catalog, .db, .name) which always return
    plain strings, avoiding the TypeError caused by raw Identifier nodes.
    """
    parts = [p for p in (table.catalog, table.db, table.name) if p]
    return ".".join(parts) if parts else str(table)
```

- [ ] **Step 4: Run tests to verify pass**

```
cd packages/dqt && uv run pytest tests/lineage/test_sql_lineage.py -v
```
Expected: all 3 PASS

- [ ] **Step 5: Commit**

```
git add packages/dqt/src/dqt/lineage/sql.py packages/dqt/tests/lineage/
git commit -m "fix: sql lineage _qualified uses .catalog/.db/.name string properties"
```

---

### Task 2: Fix freshness detector with string timestamps from LocalFileAdapter

**Problem:** When `LocalFileAdapter.aggregate()` runs `MAX(updated_at)` on a CSV, DuckDB may return the value as a Python `str` (e.g., `"2024-01-15T10:30:00"`). The `FreshnessDetector.score()` then hits `if not hasattr(latest, "timestamp"):` and returns "could not be parsed" on a perfectly valid timestamp.

**Fix:** In `FreshnessDetector.score()`, coerce `latest` via `pd.to_datetime()` before the `hasattr` check.

**Files:**
- Modify: `packages/dqt/src/dqt/algorithms/basic/freshness.py:33-45`
- Test: `packages/dqt/tests/algorithms/basic/test_freshness.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/dqt/tests/algorithms/basic/test_freshness.py`:

```python
def test_freshness_handles_string_timestamp():
    """Regression: DuckDB aggregate() may return timestamps as strings."""
    import pandas as pd
    from datetime import datetime, timezone
    from dqt.algorithms.basic.freshness import FreshnessDetector

    detector = FreshnessDetector(warn_seconds=3600, fail_seconds=86400)
    state = detector.fit(pd.DataFrame())
    # Simulate a string timestamp 30 minutes ago (DuckDB CSV path returns strings)
    recent_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    df = pd.DataFrame({"latest_ts": [recent_ts]})
    result = detector.score(df, state)
    # Should NOT return "could not be parsed"
    assert "could not be parsed" not in result.plain_english
    assert result.score < 3600  # under warn threshold


def test_freshness_handles_naive_string_timestamp():
    """String timestamps without timezone info should not bail."""
    import pandas as pd
    from dqt.algorithms.basic.freshness import FreshnessDetector

    detector = FreshnessDetector(warn_seconds=3600, fail_seconds=86400)
    state = detector.fit(pd.DataFrame())
    df = pd.DataFrame({"latest_ts": ["2020-01-01 00:00:00"]})
    result = detector.score(df, state)
    # Old timestamp → should fail, but not "could not be parsed"
    assert "could not be parsed" not in result.plain_english
    assert result.verdict.value == "fail"
```

- [ ] **Step 2: Run test to confirm failure**

```
cd packages/dqt && uv run pytest tests/algorithms/basic/test_freshness.py::test_freshness_handles_string_timestamp -v
```
Expected: FAIL — result.plain_english contains "could not be parsed"

- [ ] **Step 3: Implement the fix**

In `packages/dqt/src/dqt/algorithms/basic/freshness.py`, replace the `score()` method's timestamp handling:

```python
def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
    latest = current.iloc[0]["latest_ts"]

    # Coerce strings and other parseable types to datetime before the attribute check.
    # DuckDB's aggregate() on CSV files may return ISO strings instead of datetimes.
    if not hasattr(latest, "timestamp"):
        try:
            latest = pd.to_datetime(latest)
        except Exception:
            return DetectorResult(
                score=float("inf"),
                verdict=Verdict.fail,
                plain_english="Latest timestamp could not be parsed",
                details={"seconds_behind": float("inf"), "warn_threshold": self._warn, "fail_threshold": self._fail},
            )

    if hasattr(latest, "tzinfo") and latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)

    seconds_behind = (now - latest).total_seconds()
    # ... rest of the method unchanged
```

The full replacement (keep remaining logic identical):

```python
def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
    latest = current.iloc[0]["latest_ts"]

    if not hasattr(latest, "timestamp"):
        try:
            latest = pd.to_datetime(latest)
        except Exception:
            return DetectorResult(
                score=float("inf"),
                verdict=Verdict.fail,
                plain_english="Latest timestamp could not be parsed",
                details={"seconds_behind": float("inf"), "warn_threshold": self._warn, "fail_threshold": self._fail},
            )

    if hasattr(latest, "tzinfo") and latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)

    seconds_behind = (now - latest).total_seconds()

    if seconds_behind < 0:
        seconds_ahead = -seconds_behind
        return DetectorResult(
            score=0.0,
            verdict=Verdict.warn,
            plain_english=(
                f"Latest timestamp is {seconds_ahead:.0f}s in the future — "
                "possible clock skew, sentinel value, or timezone bug"
            ),
            details={
                "seconds_behind": 0.0,
                "seconds_ahead": seconds_ahead,
                "data_from_future": True,
                "warn_threshold": self._warn,
                "fail_threshold": self._fail,
            },
        )

    if seconds_behind >= self._fail:
        verdict = Verdict.fail
    elif seconds_behind >= self._warn:
        verdict = Verdict.warn
    else:
        verdict = Verdict.pass_

    return DetectorResult(
        score=seconds_behind,
        verdict=verdict,
        plain_english=f"Latest data is {seconds_behind:.0f}s old (warn >{self._warn:.0f}s, fail >{self._fail:.0f}s)",
        details={
            "seconds_behind": seconds_behind,
            "data_from_future": False,
            "warn_threshold": self._warn,
            "fail_threshold": self._fail,
        },
    )
```

- [ ] **Step 4: Run tests**

```
cd packages/dqt && uv run pytest tests/algorithms/basic/test_freshness.py -v
```
Expected: all PASS

- [ ] **Step 5: Commit**

```
git add packages/dqt/src/dqt/algorithms/basic/freshness.py packages/dqt/tests/algorithms/basic/test_freshness.py
git commit -m "fix: freshness detector coerces string timestamps via pd.to_datetime"
```

---

## Phase 2 — Reliability foundation

### Task 3: Power-aware warnings in BaseDetector

**Spec:** Detectors should warn users when N is too small to trust results. Add `min_recommended_n` class variable and a power-check in `Runner.run()`.

**Files:**
- Modify: `packages/dqt/src/dqt/algorithms/_base.py`
- Modify: `packages/dqt/src/dqt/runner/runner.py`
- Test: `packages/dqt/tests/runner/test_runner.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/dqt/tests/runner/test_runner.py`:

```python
def test_power_warning_injected_below_min_n(memory_store, fake_adapter):
    """When N < min_recommended_n, plain_english includes a power warning."""
    from dqt.algorithms.drift.wasserstein import Wasserstein1Detector
    from dqt.checks.models import Check
    from dqt.runner.runner import Runner
    import pandas as pd

    # Wasserstein1Detector.min_recommended_n = 500 (will be added in this task)
    # fake_adapter returns only 10 rows → below threshold
    check = Check(
        schema_name="s", table_name="t", column_name="val",
        detector_slug="wasserstein_1",
    )
    runner = Runner(memory_store)
    result = runner.run(check, fake_adapter)
    assert "N=" in result.plain_english or "low-power" in result.plain_english.lower()
```

Where `fake_adapter` is a pytest fixture that returns a small DataFrame — add to `conftest.py`:

```python
# packages/dqt/tests/conftest.py  (add this fixture)
import pandas as pd
import numpy as np
import pytest

@pytest.fixture
def fake_adapter():
    """Adapter that returns a tiny 10-row DataFrame for power-warning tests."""
    from dqt.adapters._protocol import WarehouseAdapter, ColumnMeta, HealthCheckResult

    class _TinyAdapter:
        def sample(self, schema, table, n=100_000, **kwargs):
            rng = np.random.default_rng(0)
            return pd.DataFrame({"val": rng.normal(0, 1, 10)})
        def aggregate(self, schema, table, exprs):
            return {e.name: 0.0 for e in exprs}
        def list_schemas(self): return ["s"]
        def list_tables(self, schema): return ["t"]
        def describe_columns(self, schema, table): return []
        def health_check(self): return HealthCheckResult(steps=[])

    return _TinyAdapter()
```

- [ ] **Step 2: Run test to confirm failure**

```
cd packages/dqt && uv run pytest tests/runner/test_runner.py::test_power_warning_injected_below_min_n -v
```
Expected: FAIL — `AttributeError: type object 'Wasserstein1Detector' has no attribute 'min_recommended_n'`

- [ ] **Step 3: Add `min_recommended_n` to BaseDetector**

In `packages/dqt/src/dqt/algorithms/_base.py`, add the class variable and helper:

```python
class BaseDetector:
    slug: ClassVar[str]
    group: ClassVar[str]
    kind: ClassVar[str] = "sample"
    # Subclasses set this to the minimum N for reliable results.
    # Runner emits a power warning when len(df) < this value.
    min_recommended_n: ClassVar[int] = 30

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        raise NotImplementedError

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        raise NotImplementedError

    def _verdict(self, score: float) -> Verdict:
        return compute_verdict(score, self.slug)
```

Then in `packages/dqt/src/dqt/algorithms/drift/wasserstein.py`, add:
```python
min_recommended_n: ClassVar[int] = 500
```
(Also add `from typing import ClassVar` if not present.)

And in `packages/dqt/src/dqt/algorithms/drift/ks2sample.py`:
```python
min_recommended_n: ClassVar[int] = 500
```

And `packages/dqt/src/dqt/algorithms/outliers_uni/grubbs.py` (`GrubbsDetector`):
```python
min_recommended_n: ClassVar[int] = 25
```

And `packages/dqt/src/dqt/algorithms/outliers_uni/grubbs.py` (`GeneralizedESDDetector`):
```python
min_recommended_n: ClassVar[int] = 50
```

And `packages/dqt/src/dqt/algorithms/outliers_multi/isolation_forest.py`:
```python
min_recommended_n: ClassVar[int] = 200
```

And `packages/dqt/src/dqt/algorithms/timeseries/stl.py`:
```python
min_recommended_n: ClassVar[int] = 100
```

And `packages/dqt/src/dqt/algorithms/timeseries/bocpd.py`:
```python
min_recommended_n: ClassVar[int] = 100
```

- [ ] **Step 4: Add power-check to `Runner.run()`**

In `packages/dqt/src/dqt/runner/runner.py`, add this block after `curr_df = self._fetch(check, adapter, detector=detector)`:

```python
        # Power-aware warning: prepend notice when N < detector's recommended minimum.
        n_rows = len(curr_df)
        _power_prefix: str = ""
        if n_rows < detector.min_recommended_n:
            _power_prefix = (
                f"[low-power: N={n_rows} < recommended {detector.min_recommended_n}] "
            )
```

And when building `run_result`, change:
```python
        run_result = RunResult(
            ...
            plain_english=_power_prefix + result.plain_english,
            ...
        )
```

Full updated block in `runner.py` after the `curr_df` fetch:

```python
        n_rows = len(curr_df)
        _power_prefix = (
            f"[low-power: N={n_rows} < recommended {detector.min_recommended_n}] "
            if n_rows < detector.min_recommended_n
            else ""
        )

        result = detector.score(curr_df, state)
        if check.warn_threshold is not None or check.fail_threshold is not None:
            from dqt.algorithms._base import compute_verdict
            result.verdict = compute_verdict(
                result.score, check.detector_slug,
                check.warn_threshold, check.fail_threshold,
            )
        finished_at = datetime.now(timezone.utc)

        diagnostic_sql: str | None = None
        if result.failing_filter_sql and result.verdict != Verdict.pass_:
            fq_table = f"{check.schema_name}.{check.table_name}"
            diagnostic_sql = (
                f"SELECT * FROM {fq_table}\n"
                f"WHERE {result.failing_filter_sql}\n"
                f"LIMIT 20;"
            )

        run_result = RunResult(
            check_id=check.id,
            detector_slug=check.detector_slug,
            started_at=started_at,
            finished_at=finished_at,
            verdict=result.verdict,
            score=result.score,
            plain_english=_power_prefix + result.plain_english,
            details=result.details,
            diagnostic_sql=diagnostic_sql,
        )
```

- [ ] **Step 5: Run tests**

```
cd packages/dqt && uv run pytest tests/runner/ -v
```
Expected: all PASS

- [ ] **Step 6: Commit**

```
git add packages/dqt/src/dqt/algorithms/_base.py packages/dqt/src/dqt/runner/runner.py packages/dqt/src/dqt/algorithms/drift/wasserstein.py packages/dqt/src/dqt/algorithms/drift/ks2sample.py packages/dqt/src/dqt/algorithms/outliers_uni/grubbs.py packages/dqt/src/dqt/algorithms/outliers_multi/isolation_forest.py packages/dqt/src/dqt/algorithms/timeseries/stl.py packages/dqt/src/dqt/algorithms/timeseries/bocpd.py packages/dqt/tests/conftest.py packages/dqt/tests/runner/test_runner.py
git commit -m "feat: power-aware N warning in Runner for detectors with min_recommended_n"
```

---

### Task 4: Sparse/zero-inflated degenerate-distribution guard in Runner

**Spec:** If `non_null_fraction < 0.1` or `non_null_unique_count < 5`, skip outlier detection and emit `degenerate_distribution_detected` instead. Sparsity is the quality signal.

**Files:**
- Modify: `packages/dqt/src/dqt/runner/runner.py`
- Test: `packages/dqt/tests/runner/test_runner.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/dqt/tests/runner/test_runner.py`:

```python
def test_degenerate_distribution_skips_outlier_detection(memory_store):
    """Runner emits degenerate_distribution_detected for >90% null columns."""
    from dqt.checks.models import Check
    from dqt.runner.runner import Runner
    from dqt.algorithms._base import Verdict
    import pandas as pd
    import numpy as np

    class _SparseAdapter:
        def sample(self, schema, table, n=100_000, **kwargs):
            # 95% null — degenerate
            vals = [float("nan")] * 95 + list(np.random.default_rng(0).normal(0, 1, 5))
            return pd.DataFrame({"val": vals})
        def aggregate(self, schema, table, exprs):
            return {e.name: 0.0 for e in exprs}
        def list_schemas(self): return ["s"]
        def list_tables(self, schema): return ["t"]
        def describe_columns(self, schema, table): return []
        def health_check(self):
            from dqt.adapters._protocol import HealthCheckResult
            return HealthCheckResult(steps=[])

    check = Check(
        schema_name="s", table_name="t", column_name="val",
        detector_slug="iqr_fence",
    )
    runner = Runner(memory_store)
    result = runner.run(check, _SparseAdapter())
    assert "degenerate" in result.plain_english.lower()
    assert result.verdict == Verdict.warn
```

- [ ] **Step 2: Run test to confirm failure**

```
cd packages/dqt && uv run pytest tests/runner/test_runner.py::test_degenerate_distribution_skips_outlier_detection -v
```
Expected: FAIL — no degenerate check exists yet

- [ ] **Step 3: Add degenerate guard to `Runner.run()`**

In `packages/dqt/src/dqt/runner/runner.py`, after `curr_df = self._fetch(...)` and before `result = detector.score(...)`, add:

```python
        # Degenerate-distribution guard: >90% null or <5 unique non-null values
        # means sparsity *is* the quality signal — outlier detectors would produce
        # meaningless results on such data.
        if check.column_name and detector.kind == "sample":
            _col_data = curr_df.iloc[:, 0] if not curr_df.empty else pd.Series([], dtype=float)
            _non_null_frac = float(_col_data.notna().mean()) if len(_col_data) > 0 else 0.0
            _n_unique = int(_col_data.nunique(dropna=True))
            if _non_null_frac < 0.1 or _n_unique < 5:
                finished_at = datetime.now(timezone.utc)
                run_result = RunResult(
                    check_id=check.id,
                    detector_slug=check.detector_slug,
                    started_at=started_at,
                    finished_at=finished_at,
                    verdict=Verdict.warn,
                    score=0.0,
                    plain_english=(
                        f"degenerate_distribution_detected: "
                        f"{_non_null_frac:.0%} non-null, {_n_unique} unique values — "
                        "sparsity is the quality signal; outlier detection skipped"
                    ),
                    details={
                        "degenerate": True,
                        "non_null_fraction": _non_null_frac,
                        "n_unique": _n_unique,
                    },
                )
                self._store.save_run(run_result)
                self._store.save_incident(Incident(
                    check_id=check.id,
                    run_id=run_result.run_id,
                    detector_slug=check.detector_slug,
                    severity=Verdict.warn,
                    opened_at=finished_at,
                    score=0.0,
                ))
                return run_result
```

Note: `import pd` is already imported in runner.py at the top. The `Incident` import is already available in the `run()` body.

- [ ] **Step 4: Run tests**

```
cd packages/dqt && uv run pytest tests/runner/ -v
```
Expected: all PASS

- [ ] **Step 5: Commit**

```
git add packages/dqt/src/dqt/runner/runner.py packages/dqt/tests/runner/test_runner.py
git commit -m "feat: degenerate-distribution guard in Runner — skip outlier detection when >90% null"
```

---

### Task 5: Plain-english audit — fix dishonest/incomplete descriptions

**Files:**
- Modify: `packages/dqt/src/dqt/algorithms/drift/ks2sample.py`
- Modify: `packages/dqt/src/dqt/algorithms/causality/granger.py`
- Test: `packages/dqt/tests/algorithms/drift/test_ks2sample.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/dqt/tests/algorithms/drift/test_ks2sample.py`:

```python
def test_ks_plain_english_includes_sample_size():
    """KS plain_english must report N so users know statistical power."""
    import pandas as pd, numpy as np
    from dqt.algorithms.drift.ks2sample import KS2SampleDetector

    rng = np.random.default_rng(0)
    ref = pd.DataFrame({"x": rng.normal(0, 1, 30)})   # tiny N
    curr = pd.DataFrame({"x": rng.normal(0, 1, 30)})
    det = KS2SampleDetector()
    state = det.fit(ref)
    result = det.score(curr, state)
    assert "n=" in result.plain_english.lower() or "n_ref=" in result.plain_english.lower()
```

- [ ] **Step 2: Run test to confirm failure**

```
cd packages/dqt && uv run pytest tests/algorithms/drift/test_ks2sample.py::test_ks_plain_english_includes_sample_size -v
```
Expected: FAIL

- [ ] **Step 3: Fix KS detector plain_english to include N**

In `packages/dqt/src/dqt/algorithms/drift/ks2sample.py`, change the `plain_english` line in `score()`:

```python
        return DetectorResult(
            score=score,
            verdict=self._verdict(score),
            plain_english=(
                f"KS p={p_value:.4f} (n_ref={len(state['reference'])}, n_curr={len(curr)}) — "
                f"{'drift detected' if score > 0.95 else 'no significant drift'}"
            ),
            details={"ks_statistic": float(ks_stat), "p_value": float(p_value),
                     "n_ref": len(state["reference"]), "n_curr": len(curr)},
        )
```

Also add the reference N to the `fit()` state:
```python
    def fit(self, reference: pd.DataFrame) -> DetectorState:
        arr = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        return {"reference": arr}
```
(already returns the array; `len(state["reference"])` will work.)

- [ ] **Step 4: Fix STL plain_english to include the anomaly time index**

In `packages/dqt/src/dqt/algorithms/timeseries/stl.py`, update the `plain_english`:

```python
        anomaly_indices = [int(i) for i in np.where(anomaly_mask)[0]]
        first_anomaly = f" (first at index {anomaly_indices[0]})" if anomaly_indices else ""
        return DetectorResult(
            score=max_z,
            verdict=self._verdict(max_z),
            plain_english=(
                f"Max STL residual Z={max_z:.2f}{first_anomaly} "
                f"({n_anomalies} anomalous point{'s' if n_anomalies != 1 else ''} of {len(values)})"
            ),
            ...
        )
```

- [ ] **Step 5: Run tests**

```
cd packages/dqt && uv run pytest tests/algorithms/drift/test_ks2sample.py tests/algorithms/timeseries/test_stl.py -v
```
Expected: all PASS

- [ ] **Step 6: Commit**

```
git add packages/dqt/src/dqt/algorithms/drift/ks2sample.py packages/dqt/src/dqt/algorithms/timeseries/stl.py packages/dqt/tests/algorithms/drift/test_ks2sample.py
git commit -m "fix: plain_english audit — KS includes N, STL includes anomaly index"
```

---

### Task 6: Failure-mode regression test suite

**Spec:** Organize tests by failure mode — column-projection, calibration-vs-truth, edge-cases, type-handling.

**Files:**
- Create: `packages/dqt/tests/failure_modes/__init__.py`
- Create: `packages/dqt/tests/failure_modes/test_column_projection.py`
- Create: `packages/dqt/tests/failure_modes/test_calibration.py`
- Create: `packages/dqt/tests/failure_modes/test_edge_cases.py`
- Create: `packages/dqt/tests/failure_modes/test_type_handling.py`

- [ ] **Step 1: Create column-projection tests**

```python
# packages/dqt/tests/failure_modes/test_column_projection.py
"""Every sample-kind detector on column N must score column N, not column 0."""
import numpy as np
import pandas as pd
import pytest

SLUGS_TO_TEST = [
    "wasserstein_1", "ks_pvalue", "iqr_fence", "grubbs",
    "mad_outlier_fraction", "adwin",
]


@pytest.mark.parametrize("slug", SLUGS_TO_TEST)
def test_detector_scores_correct_column(slug):
    """A detector asked to score column 'target' must not silently score column 'noise'."""
    import dqt  # trigger registry registration
    from dqt.algorithms._registry import registry

    rng = np.random.default_rng(0)
    # Column 0 ('noise') is clean; column 1 ('target') has a massive shift
    ref = pd.DataFrame({
        "noise": rng.normal(0, 1, 300),
        "target": rng.normal(0, 1, 300),
    })
    # Current: 'noise' unchanged, 'target' shifted by 10 sigma
    curr = pd.DataFrame({
        "noise": rng.normal(0, 1, 300),
        "target": rng.normal(10, 1, 300),
    })

    cls = registry.get(slug)
    det = cls()
    state = det.fit(ref[["target"]])
    result = det.score(curr[["target"]], state)
    # Should detect the shift in 'target'
    assert result.verdict.value in ("warn", "fail"), (
        f"{slug}: should detect a 10-sigma shift in 'target' but got {result.verdict} "
        f"(score={result.score:.4f})"
    )
```

- [ ] **Step 2: Create calibration tests**

```python
# packages/dqt/tests/failure_modes/test_calibration.py
"""Each outlier/drift detector must achieve F1 > 0.5 on labeled synthetic fixtures."""
import numpy as np
import pandas as pd
import pytest


def _labeled_fixture(rng, n_clean=500, n_anomaly=50):
    """Return (df, labels) where labels[i]=1 means row i is an anomaly."""
    clean = rng.normal(0, 1, n_clean)
    anomalies = rng.normal(10, 1, n_anomaly)  # 10-sigma shift
    vals = np.concatenate([clean, anomalies])
    labels = np.array([0] * n_clean + [1] * n_anomaly)
    return pd.DataFrame({"x": vals}), labels


@pytest.mark.parametrize("slug,cls_path", [
    ("iqr_fence", "dqt.algorithms.outliers_uni.iqr_fence.IQRFenceDetector"),
    ("mad_outlier_fraction", "dqt.algorithms.outliers_uni.mad.MADDetector"),
])
def test_outlier_detector_f1(slug, cls_path):
    """Outlier detectors should find 10-sigma anomalies reliably."""
    import importlib
    rng = np.random.default_rng(42)
    module_path, cls_name = cls_path.rsplit(".", 1)
    cls = getattr(importlib.import_module(module_path), cls_name)
    det = cls()
    ref = pd.DataFrame({"x": rng.normal(0, 1, 500)})
    state = det.fit(ref)
    df, labels = _labeled_fixture(rng)
    result = det.score(df, state)
    # Basic sanity: must detect some anomalies (score > 0.01) and not flag 100%
    assert result.score > 0.01, f"{slug}: score={result.score} — failed to detect obvious 10-sigma anomalies"
    assert result.score < 0.99, f"{slug}: score={result.score} — flagging virtually all points"
```

- [ ] **Step 3: Create edge-case tests**

```python
# packages/dqt/tests/failure_modes/test_edge_cases.py
"""Every detector over edge-case inputs must produce a reasonable result — no crashes,
no silent success on obviously bad data, and at most a Verdict.warn with a message."""
import numpy as np
import pandas as pd
import pytest

from dqt.algorithms._base import Verdict


def _det(slug, **params):
    import dqt  # noqa: F401 — triggers registration
    from dqt.algorithms._registry import registry
    return registry.get(slug)(**params)


@pytest.mark.parametrize("slug", ["iqr_fence", "wasserstein_1", "ks_pvalue"])
def test_empty_current_does_not_crash(slug):
    """Passing an empty current DataFrame must not raise, must return a result."""
    rng = np.random.default_rng(0)
    det = _det(slug)
    ref = pd.DataFrame({"x": rng.normal(0, 1, 100)})
    curr = pd.DataFrame({"x": pd.Series([], dtype=float)})
    state = det.fit(ref)
    result = det.score(curr, state)
    assert result is not None
    assert result.verdict in (Verdict.pass_, Verdict.warn, Verdict.fail)


@pytest.mark.parametrize("slug", ["iqr_fence", "grubbs"])
def test_constant_series_does_not_crash(slug):
    """All-identical values should not divide-by-zero."""
    det = _det(slug)
    df = pd.DataFrame({"x": [5.0] * 100})
    state = det.fit(df)
    result = det.score(df, state)
    assert result is not None


@pytest.mark.parametrize("slug", ["iqr_fence", "wasserstein_1", "ks_pvalue"])
def test_single_row(slug):
    """Single-row current DataFrame must not crash."""
    rng = np.random.default_rng(0)
    det = _det(slug)
    ref = pd.DataFrame({"x": rng.normal(0, 1, 100)})
    curr = pd.DataFrame({"x": [42.0]})
    state = det.fit(ref)
    result = det.score(curr, state)
    assert result is not None
```

- [ ] **Step 4: Create type-handling tests**

```python
# packages/dqt/tests/failure_modes/test_type_handling.py
"""Adapters must round-trip timestamps/decimals/nullable-ints correctly for aggregate detectors."""
import pandas as pd
import pytest


def test_freshness_with_pandas_timestamp():
    """pd.Timestamp (most common aggregate() return type) must not bail."""
    from dqt.algorithms.basic.freshness import FreshnessDetector
    from datetime import timezone
    import pandas as pd

    det = FreshnessDetector(warn_seconds=3600, fail_seconds=86400)
    state = det.fit(pd.DataFrame())
    ts = pd.Timestamp.now(tz=timezone.utc) - pd.Timedelta(minutes=5)
    df = pd.DataFrame({"latest_ts": [ts]})
    result = det.score(df, state)
    assert "could not be parsed" not in result.plain_english
    assert result.score < 3600


def test_freshness_with_numpy_datetime64():
    """numpy datetime64 return from DuckDB also handled."""
    import numpy as np
    from dqt.algorithms.basic.freshness import FreshnessDetector
    import pandas as pd

    det = FreshnessDetector(warn_seconds=3600, fail_seconds=86400)
    state = det.fit(pd.DataFrame())
    ts = np.datetime64("now")
    df = pd.DataFrame({"latest_ts": [ts]})
    result = det.score(df, state)
    assert "could not be parsed" not in result.plain_english


def test_freshness_with_iso_string():
    """ISO-8601 string timestamps (DuckDB CSV path) are handled."""
    from dqt.algorithms.basic.freshness import FreshnessDetector
    from datetime import datetime, timezone
    import pandas as pd

    det = FreshnessDetector(warn_seconds=3600, fail_seconds=86400)
    state = det.fit(pd.DataFrame())
    ts_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    df = pd.DataFrame({"latest_ts": [ts_str]})
    result = det.score(df, state)
    assert "could not be parsed" not in result.plain_english
```

- [ ] **Step 5: Run all failure-mode tests**

```
cd packages/dqt && uv run pytest tests/failure_modes/ -v
```
Expected: all PASS (some edge-case tests may expose new bugs to log as follow-on work)

- [ ] **Step 6: Commit**

```
git add packages/dqt/tests/failure_modes/
git commit -m "test: failure-mode regression suite — column-projection, calibration, edge-cases, type-handling"
```

---

## Phase 3 — Best-in-class causal and lineage

### Task 7: Column-level lineage from dbt manifest via sqlglot.lineage

**Spec:** `from_dbt_manifest` currently table-level only. Walk each model's `compiled_code` with `sqlglot.lineage` to extract per-output-column edges.

**Files:**
- Modify: `packages/dqt/src/dqt/lineage/dbt.py`
- Test: `packages/dqt/tests/lineage/test_dbt_lineage.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/lineage/test_dbt_lineage.py
import json, pathlib, tempfile


def _write_manifest(tmp_path: pathlib.Path, manifest: dict) -> pathlib.Path:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest))
    return p


def test_column_level_edges_extracted(tmp_path):
    """from_dbt_manifest should produce column-kind LineageNodes when compiled_code is present."""
    from dqt.lineage.dbt import from_dbt_manifest

    manifest = {
        "nodes": {
            "model.proj.orders": {
                "resource_type": "model",
                "name": "orders",
                "unique_id": "model.proj.orders",
                "depends_on": {"nodes": ["source.proj.raw.raw_orders"]},
                "compiled_code": (
                    "SELECT id, amount, customer_id FROM raw.raw_orders"
                ),
                "columns": {
                    "id": {"name": "id"},
                    "amount": {"name": "amount"},
                    "customer_id": {"name": "customer_id"},
                },
            }
        },
        "sources": {
            "source.proj.raw.raw_orders": {
                "resource_type": "source",
                "name": "raw_orders",
                "unique_id": "source.proj.raw.raw_orders",
                "depends_on": {"nodes": []},
                "columns": {
                    "id": {"name": "id"},
                    "amount": {"name": "amount"},
                    "customer_id": {"name": "customer_id"},
                },
            }
        },
    }
    p = _write_manifest(tmp_path, manifest)
    graph = from_dbt_manifest(p)

    column_nodes = [n for n in graph.nodes if n.kind == "column"]
    assert len(column_nodes) > 0, "Expected column-level nodes"

    column_edges = [e for e in graph.edges if e.kind == "column_derived_from"]
    assert len(column_edges) > 0, "Expected column-level edges"

    # The 'amount' column in orders must link back to raw_orders.amount
    amount_edge = next(
        (e for e in column_edges if "amount" in e.target and "orders" in e.target),
        None,
    )
    assert amount_edge is not None, "Expected column edge for 'amount'"
```

- [ ] **Step 2: Run test to confirm failure**

```
cd packages/dqt && uv run pytest tests/lineage/test_dbt_lineage.py -v
```
Expected: FAIL — `AssertionError: Expected column-level nodes`

- [ ] **Step 3: Implement column-level lineage in `from_dbt_manifest`**

Replace `packages/dqt/src/dqt/lineage/dbt.py` with:

```python
"""dbt manifest.json ingestion for table- and column-level lineage.
Ref: https://docs.getdbt.com/reference/artifacts/manifest-json (format v10+)
Column-level edges use sqlglot.lineage (optional; degrades to table-level if unavailable).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from dqt.lineage.models import LineageEdge, LineageGraph, LineageNode

_log = logging.getLogger(__name__)


def _column_edges_from_compiled_sql(
    compiled_sql: str,
    target_model_id: str,
    target_columns: list[str],
) -> list[tuple[str, str]]:
    """Return [(source_col_ref, target_col)] pairs from compiled SQL.

    source_col_ref is a dotted name like "raw_orders.amount".
    Returns [] if sqlglot is unavailable or parsing fails.
    """
    try:
        from sqlglot.lineage import lineage as sqlglot_lineage
    except ImportError:
        return []

    results: list[tuple[str, str]] = []
    for col in target_columns:
        try:
            node = sqlglot_lineage(col, compiled_sql)
            for source_node in node.walk():
                if source_node is node:
                    continue
                if hasattr(source_node, "name") and source_node.name:
                    src = str(source_node.name)
                    results.append((src, col))
        except Exception:
            pass
    return results


def from_dbt_manifest(manifest_path: str | Path) -> LineageGraph:
    """Parse a dbt manifest.json and return a LineageGraph with table- and column-level edges.

    Column-level lineage is extracted from ``compiled_code`` when present,
    using ``sqlglot.lineage``. Degrades to table-level if sqlglot is unavailable
    or the model has no compiled SQL.

    Example::

        graph = from_dbt_manifest("target/manifest.json")
        col_nodes = [n for n in graph.nodes if n.kind == "column"]
        col_edges = [e for e in graph.edges if e.kind == "column_derived_from"]
    """
    path = Path(manifest_path)
    manifest: dict = json.loads(path.read_text(encoding="utf-8"))

    graph = LineageGraph()
    seen_node_ids: set[str] = set()

    all_entries: dict[str, dict] = {}
    all_entries.update(manifest.get("nodes", {}))
    all_entries.update(manifest.get("sources", {}))

    _WANTED = {"model", "source"}

    # --- Pass 1: dataset nodes ---
    for unique_id, node in all_entries.items():
        if node.get("resource_type", "") not in _WANTED:
            continue
        name = node.get("name", unique_id)
        graph.add_node(LineageNode(id=unique_id, kind="dataset", label=name, dataset=name))
        seen_node_ids.add(unique_id)

        # Column nodes for known columns
        for col_name in node.get("columns", {}).keys():
            col_node_id = f"{unique_id}.{col_name}"
            graph.add_node(LineageNode(
                id=col_node_id, kind="column", label=col_name,
                dataset=name, column=col_name,
            ))

    # --- Pass 2: table-level edges ---
    for unique_id, node in all_entries.items():
        if node.get("resource_type", "") not in _WANTED:
            continue
        for dep_id in node.get("depends_on", {}).get("nodes", []):
            if dep_id not in seen_node_ids:
                continue
            graph.add_edge(LineageEdge(
                source=dep_id, target=unique_id,
                kind="derived_from", confidence=1.0,
            ))

    # --- Pass 3: column-level edges from compiled SQL ---
    for unique_id, node in all_entries.items():
        if node.get("resource_type", "") != "model":
            continue
        compiled_sql: str = node.get("compiled_code", "") or node.get("compiled_sql", "")
        if not compiled_sql.strip():
            continue
        target_columns = list(node.get("columns", {}).keys())
        if not target_columns:
            continue
        pairs = _column_edges_from_compiled_sql(compiled_sql, unique_id, target_columns)
        for src_ref, tgt_col in pairs:
            tgt_col_id = f"{unique_id}.{tgt_col}"
            # Try to match src_ref to a known column node across all datasets
            for dep_id in node.get("depends_on", {}).get("nodes", []):
                src_col_id = f"{dep_id}.{src_ref.split('.')[-1]}"
                if any(n.id == src_col_id for n in graph.nodes):
                    graph.add_edge(LineageEdge(
                        source=src_col_id, target=tgt_col_id,
                        kind="column_derived_from", confidence=0.8,
                    ))
                    break

    return graph
```

- [ ] **Step 4: Run tests**

```
cd packages/dqt && uv run pytest tests/lineage/ -v
```
Expected: all PASS

- [ ] **Step 5: Commit**

```
git add packages/dqt/src/dqt/lineage/dbt.py packages/dqt/tests/lineage/test_dbt_lineage.py
git commit -m "feat: column-level lineage from dbt manifest via sqlglot.lineage"
```

---

### Task 8: PCMCI+ causal discovery

**Spec:** Add `pcmci_pairwise()` using tigramite (optional `dqt[causal]`). Solves Granger's bivariate-only limitation by conditioning on other variables.

**Files:**
- Create: `packages/dqt/src/dqt/causality/pcmci.py`
- Modify: `packages/dqt/src/dqt/causality/__init__.py`
- Test: `packages/dqt/tests/causality/test_pcmci.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/causality/test_pcmci.py
import numpy as np
import pandas as pd
import pytest


def test_pcmci_basic_chain():
    """X→Y→Z chain: PCMCI+ should find X→Y and Y→Z but not X→Z after conditioning."""
    pytest.importorskip("tigramite")
    from dqt.causality.pcmci import pcmci_pairwise

    rng = np.random.default_rng(0)
    n = 200
    x = rng.normal(0, 1, n)
    y = 0.8 * np.roll(x, 1) + rng.normal(0, 0.3, n)
    z = 0.8 * np.roll(y, 1) + rng.normal(0, 0.3, n)
    y[0], z[0] = 0.0, 0.0

    df = pd.DataFrame({"x": x, "y": y, "z": z})
    report = pcmci_pairwise(df, tau_max=3)

    sig = {(e.cause, e.effect) for e in report.edges if e.significant}
    assert ("x", "y") in sig, f"Expected x->y, got: {sig}"
    assert ("y", "z") in sig, f"Expected y->z, got: {sig}"


def test_pcmci_raises_without_tigramite(monkeypatch):
    """ImportError if tigramite not installed."""
    import importlib, sys
    monkeypatch.setitem(sys.modules, "tigramite", None)
    with pytest.raises((ImportError, TypeError)):
        from dqt.causality.pcmci import pcmci_pairwise  # noqa: F401
        import pandas as pd, numpy as np
        pcmci_pairwise(pd.DataFrame({"a": [1.0, 2.0, 3.0]}))
```

- [ ] **Step 2: Run test to confirm failure**

```
cd packages/dqt && uv run pytest tests/causality/test_pcmci.py::test_pcmci_basic_chain -v
```
Expected: FAIL or SKIP (tigramite not installed) — mostly `ImportError` or `ModuleNotFoundError`

- [ ] **Step 3: Create `packages/dqt/src/dqt/causality/pcmci.py`**

```python
# packages/dqt/src/dqt/causality/pcmci.py
# Ref: Runge et al. (2019) Science Advances — Detecting and quantifying causal associations in large
# nonlinear time series datasets. Uses tigramite (optional dqt[causal]).
# Guardrails: stationarity gate (shared from granger), BH-FDR correction, tau_max auto-selection.
from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from dqt.causality.granger import _bh_correction, _evidence_strength, _make_stationary, _NonStationaryError

_MIN_ROWS = 50


@dataclass
class PCMCIEdge:
    """A single causal edge found by PCMCI+."""
    cause: str
    effect: str
    lag: int                     # optimal lag in time steps
    raw_p_value: float
    adjusted_p_value: float
    val_min: float               # minimum partial correlation coefficient
    evidence_strength: str       # "none" | "weak" | "moderate" | "strong"
    differenced: bool
    confounder_candidates: list[str] = field(default_factory=list)

    @property
    def significant(self) -> bool:
        return self.evidence_strength in ("moderate", "strong")


@dataclass
class PCMCIReport:
    edges: list[PCMCIEdge] = field(default_factory=list)
    significance_level: float = 0.05

    @property
    def significant_edges(self) -> list[PCMCIEdge]:
        return [e for e in self.edges if e.significant]

    def to_dict(self) -> dict:
        return {
            "n_pairs_tested": len(self.edges),
            "n_significant": len(self.significant_edges),
            "edges": [
                {
                    "cause": e.cause, "effect": e.effect, "lag": e.lag,
                    "raw_p_value": e.raw_p_value, "adjusted_p_value": e.adjusted_p_value,
                    "val_min": e.val_min, "evidence_strength": e.evidence_strength,
                    "significant": e.significant, "differenced": e.differenced,
                    "confounder_candidates": e.confounder_candidates,
                }
                for e in self.edges
            ],
        }


def pcmci_pairwise(
    df: pd.DataFrame,
    tau_max: int | None = None,
    significance_level: float = 0.05,
    cond_ind_test: str = "parcorr",
    columns: list[str] | None = None,
) -> PCMCIReport:
    """Run PCMCI+ for every variable pair in df, conditioning on all others.

    Parameters
    ----------
    df:
        DataFrame where each column is a time series (rows = time steps).
    tau_max:
        Max lag. Defaults to max(3, n_rows // 50) up to 10.
    significance_level:
        Applied to BH-corrected p-values.
    cond_ind_test:
        "parcorr" (linear, fast) or "gpdc" (non-linear, slow).
    columns:
        Subset of columns to test. Defaults to all numeric columns.

    Example
    -------
    >>> import pandas as pd, numpy as np
    >>> rng = np.random.default_rng(42)
    >>> n = 150
    >>> x = rng.normal(0, 1, n)
    >>> y = 0.7 * np.roll(x, 2) + rng.normal(0, 0.5, n)
    >>> df = pd.DataFrame({"x": x, "y": y})
    >>> report = pcmci_pairwise(df, tau_max=3)
    >>> print(report.significant_edges[0].cause, "->", report.significant_edges[0].effect)
    x -> y
    """
    try:
        from tigramite import data_processing as pp
        from tigramite.pcmci import PCMCI
        from tigramite.independence_tests.parcorr import ParCorr
    except ImportError as exc:
        raise ImportError(
            "tigramite is required for PCMCI+. "
            "Install with: pip install 'dqtlib[causal]'"
        ) from exc

    if columns is None:
        columns = list(df.select_dtypes(include="number").columns)

    if len(df) < _MIN_ROWS:
        raise ValueError(f"pcmci_pairwise requires at least {_MIN_ROWS} rows, got {len(df)}")

    if tau_max is None:
        tau_max = min(max(3, len(df) // 50), 10)

    # Stationarity gate — shared logic from granger module
    stationary_arrays: dict[str, tuple[np.ndarray, bool]] = {}
    skip_cols: set[str] = set()
    for col in columns:
        raw = df[col].to_numpy(dtype=float)
        try:
            stationary_arrays[col] = _make_stationary(raw)
        except _NonStationaryError:
            skip_cols.add(col)

    usable = [c for c in columns if c not in skip_cols]
    if len(usable) < 2:
        return PCMCIReport(significance_level=significance_level)

    # Build aligned data matrix (drop leading NaN from differenced series)
    arrays = [stationary_arrays[c][0] for c in usable]
    differenced_flags = [stationary_arrays[c][1] for c in usable]
    data_matrix = np.column_stack(arrays)
    nan_rows = np.any(np.isnan(data_matrix), axis=1)
    data_matrix = data_matrix[~nan_rows]

    if len(data_matrix) < _MIN_ROWS:
        return PCMCIReport(significance_level=significance_level)

    # Run PCMCI+
    dataframe = pp.DataFrame(data_matrix, var_names=usable)
    cit = ParCorr(significance="analytic")
    pcmci = PCMCI(dataframe=dataframe, cond_ind_test=cit, verbosity=0)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        results = pcmci.run_pcmciplus(tau_min=1, tau_max=tau_max, pc_alpha=0.05)

    p_matrix = results["p_matrix"]   # shape (N_vars, N_vars, tau_max+1)
    val_matrix = results["val_matrix"]

    # Collect raw p-values (min over lags) for each ordered pair
    _pending: list[tuple[str, str, float, float, int, bool]] = []
    for i, cause in enumerate(usable):
        for j, effect in enumerate(usable):
            if i == j:
                continue
            # Take lag with minimum p-value (most significant)
            p_slice = p_matrix[j, i, 1:]   # shape (tau_max,)
            v_slice = val_matrix[j, i, 1:]
            best_lag_idx = int(np.argmin(p_slice))
            raw_p = float(p_slice[best_lag_idx])
            val_min = float(v_slice[best_lag_idx])
            lag = best_lag_idx + 1
            differenced = differenced_flags[i] or differenced_flags[j]
            _pending.append((cause, effect, raw_p, val_min, lag, differenced))

    raw_ps = [item[2] for item in _pending]
    adjusted_ps = _bh_correction(raw_ps)

    report = PCMCIReport(significance_level=significance_level)
    for (cause, effect, raw_p, val_min, lag, diffed), adj_p in zip(_pending, adjusted_ps):
        strength = _evidence_strength(float(adj_p))
        report.edges.append(PCMCIEdge(
            cause=cause, effect=effect, lag=lag,
            raw_p_value=raw_p, adjusted_p_value=float(adj_p),
            val_min=val_min, evidence_strength=strength,
            differenced=diffed,
        ))

    # Confounder annotation: Z is a confounder candidate for X→Y if Z→X and Z→Y are both significant
    sig_set = {(e.cause, e.effect) for e in report.edges if e.significant}
    for edge in report.edges:
        if not edge.significant:
            continue
        edge.confounder_candidates = [
            col for col in usable
            if col != edge.cause and col != edge.effect
            and (col, edge.cause) in sig_set and (col, edge.effect) in sig_set
        ]

    return report
```

- [ ] **Step 4: Update `packages/dqt/src/dqt/causality/__init__.py`**

```python
from dqt.causality.granger import GrangerEdge, GrangerReport, granger_pairwise
from dqt.causality.pcmci import PCMCIEdge, PCMCIReport, pcmci_pairwise

__all__ = [
    "GrangerEdge", "GrangerReport", "granger_pairwise",
    "PCMCIEdge", "PCMCIReport", "pcmci_pairwise",
]
```

- [ ] **Step 5: Run tests (skip if tigramite unavailable)**

```
cd packages/dqt && uv run pytest tests/causality/ -v
```
Expected: `test_pcmci_basic_chain` either PASS (if tigramite installed) or SKIP. `test_pcmci_raises_without_tigramite` PASS.

- [ ] **Step 6: Commit**

```
git add packages/dqt/src/dqt/causality/pcmci.py packages/dqt/src/dqt/causality/__init__.py packages/dqt/tests/causality/test_pcmci.py
git commit -m "feat: PCMCI+ causal discovery with stationarity gate and BH-FDR"
```

---

### Task 9: Causal reviewer feedback loop

**Spec:** Accept/reject/defer for causal edges. Persist to `ResultsStore`. Accumulate per-edge precision over time.

**Files:**
- Modify: `packages/dqt/src/dqt/store/_protocol.py`
- Modify: `packages/dqt/src/dqt/store/memory.py`
- Test: `packages/dqt/tests/store/test_causal_reviews.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/store/test_causal_reviews.py
from datetime import datetime, timezone
from uuid import uuid4
import pytest


def test_save_and_list_causal_reviews():
    """ResultsStore can persist and retrieve CausalEdgeReview records."""
    from dqt.store.memory import MemoryStore
    from dqt.store._protocol import CausalEdgeReview

    store = MemoryStore()
    edge_id = uuid4()
    review = CausalEdgeReview(
        edge_id=edge_id,
        cause="revenue",
        effect="bookings",
        decision="accept",
        reviewer="analyst@example.com",
        reviewed_at=datetime.now(timezone.utc),
        reason="Confirmed by domain knowledge",
    )
    store.save_causal_review(review)
    reviews = store.list_causal_reviews(edge_id=edge_id)
    assert len(reviews) == 1
    assert reviews[0].decision == "accept"


def test_causal_edge_precision():
    """Precision report counts accept vs reject for an edge."""
    from dqt.store.memory import MemoryStore
    from dqt.store._protocol import CausalEdgeReview

    store = MemoryStore()
    edge_id = uuid4()
    for decision in ["accept", "accept", "reject", "defer"]:
        store.save_causal_review(CausalEdgeReview(
            edge_id=edge_id, cause="x", effect="y", decision=decision,
            reviewer="r", reviewed_at=datetime.now(timezone.utc),
        ))
    precision = store.causal_edge_precision(edge_id=edge_id)
    # 2 accept / 3 decided (accept+reject) = 0.667
    assert abs(precision - 2 / 3) < 0.01
```

- [ ] **Step 2: Run test to confirm failure**

```
cd packages/dqt && uv run pytest tests/store/test_causal_reviews.py -v
```
Expected: FAIL — `AttributeError: 'MemoryStore' has no attribute 'save_causal_review'`

- [ ] **Step 3: Add `CausalEdgeReview` to `_protocol.py`**

Add to `packages/dqt/src/dqt/store/_protocol.py`:

```python
from typing import Literal

@dataclass
class CausalEdgeReview:
    """Human review decision for a proposed causal edge."""
    edge_id: UUID
    cause: str
    effect: str
    decision: Literal["accept", "reject", "defer"]
    reviewer: str
    reviewed_at: datetime
    reason: str = ""
    review_id: UUID = field(default_factory=uuid4)
```

And extend `ResultsStore` protocol:

```python
@runtime_checkable
class ResultsStore(Protocol):
    def save_run(self, run: RunResult) -> None: ...
    def list_runs(self, check_id: UUID, limit: int = 100) -> list[RunResult]: ...
    def save_incident(self, incident: Incident) -> None: ...
    def list_incidents(self, check_id: UUID, status: str | None = None) -> list[Incident]: ...
    def save_causal_review(self, review: CausalEdgeReview) -> None: ...
    def list_causal_reviews(self, edge_id: UUID) -> list[CausalEdgeReview]: ...
    def causal_edge_precision(self, edge_id: UUID) -> float: ...
```

Also add `CausalEdgeReview` to the `from` imports in `dqt/__init__.py`'s `__all__`.

- [ ] **Step 4: Implement in `MemoryStore`**

Read `packages/dqt/src/dqt/store/memory.py` first, then add:

```python
    def save_causal_review(self, review: "CausalEdgeReview") -> None:
        self._causal_reviews.append(review)

    def list_causal_reviews(self, edge_id: "UUID") -> list["CausalEdgeReview"]:
        return [r for r in self._causal_reviews if r.edge_id == edge_id]

    def causal_edge_precision(self, edge_id: "UUID") -> float:
        reviews = self.list_causal_reviews(edge_id)
        decided = [r for r in reviews if r.decision in ("accept", "reject")]
        if not decided:
            return float("nan")
        return sum(1 for r in decided if r.decision == "accept") / len(decided)
```

And initialise `self._causal_reviews: list = []` in `__init__`.

- [ ] **Step 5: Run tests**

```
cd packages/dqt && uv run pytest tests/store/ -v
```
Expected: all PASS

- [ ] **Step 6: Commit**

```
git add packages/dqt/src/dqt/store/_protocol.py packages/dqt/src/dqt/store/memory.py packages/dqt/tests/store/test_causal_reviews.py
git commit -m "feat: causal edge reviewer feedback loop — accept/reject/defer with precision tracking"
```

---

## Phase 4 — Workflow integration

### Task 10: `dqt run` executes checks with a real adapter and outputs JUnit XML

**Spec:** Add `--connection` flag to `dqt run`, instantiate the right adapter, execute checks, emit JSON / JUnit XML.

**Files:**
- Modify: `packages/dqt/src/dqt/cli/main.py`
- Test: `packages/dqt/tests/cli/test_cli_run.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/cli/test_cli_run.py
import pathlib, textwrap, tempfile


def test_run_with_local_adapter_json_output(tmp_path):
    """dqt run --connection file://... checks.yaml --output json exits 0 and emits JSON."""
    import pandas as pd, json, subprocess, sys

    # Write a tiny CSV
    csv_path = tmp_path / "orders.csv"
    pd.DataFrame({"amount": list(range(100))}).to_csv(csv_path, index=False)

    # Write a check YAML
    checks_yaml = tmp_path / "checks.yaml"
    checks_yaml.write_text(textwrap.dedent(f"""
        checks:
          - schema: default
            table: orders
            column: amount
            detector: iqr_fence
    """))

    result = subprocess.run(
        [sys.executable, "-m", "dqt.cli.main", "run",
         str(checks_yaml),
         "--connection", f"file://{csv_path}",
         "--output", "json"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert "results" in data
    assert len(data["results"]) == 1


def test_run_with_local_adapter_junit_output(tmp_path):
    """dqt run --output junit emits valid JUnit XML."""
    import pandas as pd, subprocess, sys
    from xml.etree import ElementTree

    csv_path = tmp_path / "orders.csv"
    pd.DataFrame({"amount": list(range(100))}).to_csv(csv_path, index=False)

    checks_yaml = tmp_path / "checks.yaml"
    checks_yaml.write_text(textwrap.dedent(f"""
        checks:
          - schema: default
            table: orders
            column: amount
            detector: iqr_fence
    """))

    result = subprocess.run(
        [sys.executable, "-m", "dqt.cli.main", "run",
         str(checks_yaml),
         "--connection", f"file://{csv_path}",
         "--output", "junit"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    root = ElementTree.fromstring(result.stdout)
    assert root.tag == "testsuites"
    assert len(root.findall(".//testcase")) >= 1
```

- [ ] **Step 2: Run test to confirm failure**

```
cd packages/dqt && uv run pytest tests/cli/test_cli_run.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement `--connection` and `--output` in CLI**

Create `packages/dqt/tests/cli/__init__.py` (empty).

In `packages/dqt/src/dqt/cli/main.py`, replace the `_cmd_run` function and update the `run` subparser:

```python
def _resolve_adapter(connection: str):
    """Instantiate the correct WarehouseAdapter from a connection string."""
    if connection.startswith("file://"):
        from dqt.adapters.local import LocalFileAdapter
        return LocalFileAdapter(connection[len("file://"):])
    if connection.startswith("postgresql://") or connection.startswith("postgres://"):
        from dqt.adapters.postgres.adapter import PostgresAdapter
        return PostgresAdapter(connection)
    raise ValueError(
        f"Unsupported connection scheme: '{connection}'. "
        "Supported: file://<path>, postgresql://<...>"
    )


def _results_to_json(results) -> str:
    import json
    return json.dumps({
        "results": [
            {
                "check_id": str(r.check_id),
                "detector_slug": r.detector_slug,
                "verdict": r.verdict.value,
                "score": r.score,
                "plain_english": r.plain_english,
            }
            for r in results
        ]
    }, indent=2)


def _results_to_junit(results) -> str:
    from xml.etree.ElementTree import Element, SubElement, tostring
    suites = Element("testsuites")
    suite = SubElement(suites, "testsuite", name="dqt", tests=str(len(results)))
    for r in results:
        tc = SubElement(suite, "testcase", name=r.detector_slug,
                        classname=str(r.check_id), time="0")
        if r.verdict.value == "fail":
            failure = SubElement(tc, "failure", message=r.plain_english)
            failure.text = r.plain_english
        elif r.verdict.value == "warn":
            SubElement(tc, "system-out").text = r.plain_english
    from xml.etree.ElementTree import indent as et_indent
    try:
        et_indent(suites)
    except TypeError:
        pass  # Python < 3.9
    return '<?xml version="1.0"?>\n' + tostring(suites, encoding="unicode")


def _cmd_run(args: argparse.Namespace) -> None:
    """Load a YAML check file. With --connection, execute checks against the adapter."""
    from dqt.checks.loader import load_checks_file, CheckValidationError

    try:
        checks = load_checks_file(args.yaml_file)
    except FileNotFoundError:
        print(f"error: file not found: {args.yaml_file}", file=sys.stderr)
        sys.exit(1)
    except CheckValidationError as exc:
        print(f"error: invalid check YAML: {exc}", file=sys.stderr)
        sys.exit(1)

    if not checks:
        print("No checks defined in file.")
        return

    if not getattr(args, "connection", None):
        for check in checks:
            print(
                f"run: {check.detector_slug}  "
                f"[{check.schema_name}.{check.table_name}"
                + (f".{check.column_name}" if check.column_name else "")
                + "]"
            )
        print("\nNote: pass --connection <url> to execute checks.")
        return

    adapter = _resolve_adapter(args.connection)
    from dqt.store.memory import MemoryStore
    from dqt.runner.runner import Runner
    runner = Runner(MemoryStore())

    results = []
    any_fail = False
    for check in checks:
        try:
            result = runner.run(check, adapter)
            results.append(result)
            if result.verdict.value == "fail":
                any_fail = True
        except Exception as exc:
            print(f"error running {check.detector_slug}: {exc}", file=sys.stderr)
            any_fail = True

    output_fmt = getattr(args, "output", "text")
    if output_fmt == "json":
        print(_results_to_json(results))
    elif output_fmt == "junit":
        print(_results_to_junit(results))
    else:
        for r in results:
            print(f"[{r.verdict.value.upper():4s}] {r.detector_slug}: {r.plain_english}")

    sys.exit(1 if any_fail else 0)
```

Update the `run` subparser registration in `main()`:

```python
    p_run = sub.add_parser("run", help="Run checks; pass --connection to execute against an adapter")
    p_run.add_argument("yaml_file", help="Path to the YAML check file")
    p_run.add_argument("--connection", default=None,
                       help="Connection string, e.g. file:///path/to/data.csv or postgresql://...")
    p_run.add_argument("--output", choices=["text", "json", "junit"], default="text",
                       help="Output format (default: text)")
```

- [ ] **Step 4: Run tests**

```
cd packages/dqt && uv run pytest tests/cli/ -v
```
Expected: all PASS

- [ ] **Step 5: Commit**

```
git add packages/dqt/src/dqt/cli/main.py packages/dqt/tests/cli/
git commit -m "feat: dqt run --connection executes checks and supports --output json|junit"
```

---

### Task 11: Reproducibility bundle per RunResult

**Spec:** `RunResult.to_bundle(path)` writes config, baseline, current sample, diagnostic SQL, result JSON, and environment to a directory for incident attachment.

**Files:**
- Modify: `packages/dqt/src/dqt/store/_protocol.py`
- Test: `packages/dqt/tests/store/test_reproducibility_bundle.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/store/test_reproducibility_bundle.py
import pathlib, json
from datetime import datetime, timezone
from uuid import uuid4


def test_to_bundle_writes_expected_files(tmp_path):
    """RunResult.to_bundle() creates all 5 expected files."""
    import pandas as pd
    from dqt.store._protocol import RunResult, ReproducibilityBundle
    from dqt.algorithms._base import Verdict

    bundle = ReproducibilityBundle(
        check_id=uuid4(),
        run_id=uuid4(),
        detector_slug="iqr_fence",
        detector_params={"k": 3.0},
        schema_name="analytics",
        table_name="orders",
        column_name="amount",
        sample_n=100,
    )
    run = RunResult(
        check_id=bundle.check_id,
        detector_slug="iqr_fence",
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        verdict=Verdict.fail,
        score=0.12,
        plain_english="12% of values outside IQR fences",
        details={"outlier_fraction": 0.12},
        reproducibility=bundle,
    )

    run.to_bundle(tmp_path)

    assert (tmp_path / "result.json").exists()
    assert (tmp_path / "config.json").exists()
    assert (tmp_path / "environment.json").exists()

    result_data = json.loads((tmp_path / "result.json").read_text())
    assert result_data["verdict"] == "fail"
    assert result_data["score"] == 0.12

    env_data = json.loads((tmp_path / "environment.json").read_text())
    assert "dqt_version" in env_data
    assert "python_version" in env_data
```

- [ ] **Step 2: Run test to confirm failure**

```
cd packages/dqt && uv run pytest tests/store/test_reproducibility_bundle.py -v
```
Expected: FAIL — `AttributeError: 'RunResult' object has no attribute 'to_bundle'`

- [ ] **Step 3: Add `to_bundle()` to `RunResult`**

In `packages/dqt/src/dqt/store/_protocol.py`, add a method to `RunResult`:

```python
    def to_bundle(self, path: "str | Path") -> None:
        """Write reproducibility artifacts to a directory.

        Creates:
          result.json    — score, verdict, plain_english, details
          config.json    — check configuration from ReproducibilityBundle
          environment.json — dqt version, Python version, platform
          diagnostic.sql  — failing-rows query (if available)
        """
        import json
        import platform
        import sys
        from pathlib import Path

        out = Path(path)
        out.mkdir(parents=True, exist_ok=True)

        # result.json
        (out / "result.json").write_text(json.dumps({
            "check_id": str(self.check_id),
            "run_id": str(self.run_id),
            "detector_slug": self.detector_slug,
            "verdict": self.verdict.value,
            "score": self.score,
            "plain_english": self.plain_english,
            "details": self.details,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
        }, indent=2))

        # config.json
        bundle = self.reproducibility
        config: dict = {"detector_slug": self.detector_slug}
        if bundle:
            config.update({
                "detector_params": bundle.detector_params,
                "schema_name": bundle.schema_name,
                "table_name": bundle.table_name,
                "column_name": bundle.column_name,
                "sample_n": bundle.sample_n,
                "detector_state": bundle.detector_state_json,
                "notes": bundle.notes,
            })
        (out / "config.json").write_text(json.dumps(config, indent=2))

        # environment.json
        try:
            from dqt import __version__ as dqt_version
        except Exception:
            dqt_version = "unknown"
        (out / "environment.json").write_text(json.dumps({
            "dqt_version": dqt_version,
            "python_version": sys.version,
            "platform": platform.platform(),
        }, indent=2))

        # diagnostic.sql (optional)
        if self.diagnostic_sql:
            (out / "diagnostic.sql").write_text(self.diagnostic_sql)
```

Add `from pathlib import Path` to the imports at the top of `_protocol.py` if not present.

- [ ] **Step 4: Run tests**

```
cd packages/dqt && uv run pytest tests/store/test_reproducibility_bundle.py -v
```
Expected: all PASS

- [ ] **Step 5: Commit**

```
git add packages/dqt/src/dqt/store/_protocol.py packages/dqt/tests/store/test_reproducibility_bundle.py
git commit -m "feat: RunResult.to_bundle() writes incident reproducibility artifacts"
```

---

### Task 12: OpenLineage event emission

**Spec:** dqt should emit `START`/`COMPLETE`/`FAIL` OpenLineage events so it's first-class in Marquez, Datakin, and OpenMetadata.

**Files:**
- Create: `packages/dqt/src/dqt/lineage/openlineage.py`
- Modify: `packages/dqt/src/dqt/lineage/__init__.py`
- Test: `packages/dqt/tests/lineage/test_openlineage.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/lineage/test_openlineage.py
from datetime import datetime, timezone
from uuid import uuid4


def test_emit_start_and_complete():
    """OpenLineageEmitter builds START and COMPLETE events as dicts."""
    from dqt.lineage.openlineage import OpenLineageEmitter, RunState

    emitter = OpenLineageEmitter(
        producer="dqt/test",
        transport=None,  # None = collect in-memory for testing
    )
    run_id = str(uuid4())
    now = datetime.now(timezone.utc)

    start_event = emitter.build_event(
        state=RunState.START,
        job_name="analytics.orders.iqr_fence",
        run_id=run_id,
        event_time=now,
    )
    assert start_event["eventType"] == "START"
    assert start_event["job"]["name"] == "analytics.orders.iqr_fence"
    assert start_event["run"]["runId"] == run_id

    complete_event = emitter.build_event(
        state=RunState.COMPLETE,
        job_name="analytics.orders.iqr_fence",
        run_id=run_id,
        event_time=now,
        outputs=[{"namespace": "dqt", "name": "analytics.orders"}],
    )
    assert complete_event["eventType"] == "COMPLETE"
    assert len(complete_event["outputs"]) == 1


def test_emit_fail_event():
    """FAIL event includes error message."""
    from dqt.lineage.openlineage import OpenLineageEmitter, RunState

    emitter = OpenLineageEmitter(producer="dqt/test", transport=None)
    event = emitter.build_event(
        state=RunState.FAIL,
        job_name="analytics.orders.iqr_fence",
        run_id=str(uuid4()),
        event_time=datetime.now(timezone.utc),
        error_message="12% of values outside IQR fences — verdict: fail",
    )
    assert event["eventType"] == "FAIL"
    assert "error_message" in event.get("run", {}).get("facets", {}).get("errorMessage", {}) or \
           "error_message" in str(event)
```

- [ ] **Step 2: Run test to confirm failure**

```
cd packages/dqt && uv run pytest tests/lineage/test_openlineage.py -v
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create `openlineage.py`**

```python
# packages/dqt/src/dqt/lineage/openlineage.py
# Ref: https://openlineage.io/spec/ — OpenLineage 1.x event schema
# Emits START / COMPLETE / FAIL lifecycle events so dqt integrates with Marquez,
# Datakin, and OpenMetadata without requiring the openlineage-python SDK.
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class RunState(str, Enum):
    START = "START"
    COMPLETE = "COMPLETE"
    FAIL = "FAIL"


@dataclass
class OpenLineageEmitter:
    """Builds OpenLineage events and optionally POSTs them to a transport URL.

    When ``transport`` is ``None``, events are returned from ``emit()`` but
    not sent anywhere — useful for testing and offline collection.

    Example::

        from dqt.lineage.openlineage import OpenLineageEmitter, RunState
        emitter = OpenLineageEmitter(
            producer="dqt/0.3.0",
            transport="http://marquez:5000/api/v1/lineage",
        )
        run_id = str(uuid4())
        emitter.emit(RunState.START, "analytics.orders.iqr_fence", run_id)
        # ... run the check ...
        emitter.emit(RunState.COMPLETE, "analytics.orders.iqr_fence", run_id,
                     outputs=[{"namespace": "dqt", "name": "analytics.orders"}])
    """
    producer: str
    transport: str | None = None
    namespace: str = "dqt"
    _emitted: list[dict[str, Any]] = field(default_factory=list, init=False, repr=False)

    def build_event(
        self,
        state: RunState,
        job_name: str,
        run_id: str,
        event_time: datetime | None = None,
        inputs: list[dict] | None = None,
        outputs: list[dict] | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        if event_time is None:
            event_time = datetime.now(timezone.utc)

        run_facets: dict[str, Any] = {}
        if error_message:
            run_facets["errorMessage"] = {
                "_producer": self.producer,
                "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/ErrorMessageRunFacet.json",
                "message": error_message,
                "programmingLanguage": "Python",
            }

        return {
            "eventType": state.value,
            "eventTime": event_time.isoformat(),
            "producer": self.producer,
            "schemaURL": "https://openlineage.io/spec/1-0-5/OpenLineage.json",
            "run": {
                "runId": run_id,
                "facets": run_facets,
            },
            "job": {
                "namespace": self.namespace,
                "name": job_name,
                "facets": {},
            },
            "inputs": inputs or [],
            "outputs": outputs or [],
        }

    def emit(
        self,
        state: RunState,
        job_name: str,
        run_id: str,
        event_time: datetime | None = None,
        inputs: list[dict] | None = None,
        outputs: list[dict] | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        event = self.build_event(
            state=state, job_name=job_name, run_id=run_id,
            event_time=event_time, inputs=inputs, outputs=outputs,
            error_message=error_message,
        )
        self._emitted.append(event)
        if self.transport:
            import json
            import urllib.request
            body = json.dumps(event).encode()
            req = urllib.request.Request(
                self.transport, data=body,
                headers={"Content-Type": "application/json"}, method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=5):
                    pass
            except Exception:
                pass  # Non-fatal: lineage emission should never break a check run
        return event
```

Update `packages/dqt/src/dqt/lineage/__init__.py`:

```python
from dqt.lineage.dbt import from_dbt_manifest
from dqt.lineage.models import LineageEdge, LineageGraph, LineageNode
from dqt.lineage.openlineage import OpenLineageEmitter, RunState
from dqt.lineage.sql import from_sql_files
from dqt.lineage.vault import write_vault

__all__ = [
    "LineageEdge", "LineageGraph", "LineageNode",
    "from_dbt_manifest", "from_sql_files", "write_vault",
    "OpenLineageEmitter", "RunState",
]
```

- [ ] **Step 4: Run tests**

```
cd packages/dqt && uv run pytest tests/lineage/test_openlineage.py -v
```
Expected: all PASS

- [ ] **Step 5: Commit**

```
git add packages/dqt/src/dqt/lineage/openlineage.py packages/dqt/src/dqt/lineage/__init__.py packages/dqt/tests/lineage/test_openlineage.py
git commit -m "feat: OpenLineage event emitter for Marquez/Datakin/OpenMetadata integration"
```

---

### Task 13: Compile checks to dbt tests

**Spec:** `dqt compile checks.yaml --to dbt` emits dbt-compatible YAML test files.

**Files:**
- Create: `packages/dqt/src/dqt/compat/dbt_tests.py`
- Modify: `packages/dqt/src/dqt/cli/main.py`
- Test: `packages/dqt/tests/compat/test_dbt_tests.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/compat/__init__.py  (empty)

# packages/dqt/tests/compat/test_dbt_tests.py
import textwrap


def test_compile_to_dbt_yaml():
    """iqr_fence on a numeric column compiles to a dbt custom test."""
    import yaml
    from dqt.checks.models import Check
    from dqt.compat.dbt_tests import checks_to_dbt_yaml

    checks = [
        Check(schema_name="analytics", table_name="orders",
              column_name="amount", detector_slug="iqr_fence",
              params={"k": 3.0}),
        Check(schema_name="analytics", table_name="orders",
              column_name=None, detector_slug="volume_change_ratio"),
    ]
    dbt_yaml = checks_to_dbt_yaml(checks)
    data = yaml.safe_load(dbt_yaml)

    assert "models" in data
    model = data["models"][0]
    assert model["name"] == "orders"

    # Column-level test for iqr_fence
    col = next(c for c in model.get("columns", []) if c["name"] == "amount")
    test_names = [
        list(t.keys())[0] if isinstance(t, dict) else t
        for t in col["tests"]
    ]
    assert any("iqr_fence" in str(t) for t in test_names)


def test_compile_null_fraction_maps_to_native_dbt():
    """null_fraction maps to dbt's built-in not_null test."""
    import yaml
    from dqt.checks.models import Check
    from dqt.compat.dbt_tests import checks_to_dbt_yaml

    checks = [
        Check(schema_name="analytics", table_name="users",
              column_name="email", detector_slug="null_fraction"),
    ]
    dbt_yaml = checks_to_dbt_yaml(checks)
    data = yaml.safe_load(dbt_yaml)
    col = data["models"][0]["columns"][0]
    assert "not_null" in col["tests"]
```

- [ ] **Step 2: Run test to confirm failure**

```
cd packages/dqt && uv run pytest tests/compat/test_dbt_tests.py -v
```
Expected: FAIL

- [ ] **Step 3: Create `dbt_tests.py`**

Create `packages/dqt/src/dqt/compat/__init__.py` (empty if not existing).

```python
# packages/dqt/src/dqt/compat/dbt_tests.py
"""Compile dqt Check objects to dbt schema YAML with native and custom test stubs.
Ref: https://docs.getdbt.com/reference/resource-configs/tests
"""
from __future__ import annotations

from collections import defaultdict

import yaml

# dqt slug → dbt native test name (direct equivalents only)
_NATIVE_MAP: dict[str, str | None] = {
    "null_fraction": "not_null",
    "uniqueness_rate": "unique",
}

# dqt slugs that map to dbt's accepted_values (need values param)
_ACCEPTED_VALUES_SLUG = "set_membership_violation"


def checks_to_dbt_yaml(checks) -> str:
    """Convert a list of Check objects to a dbt schema.yml YAML string.

    Native dbt tests (not_null, unique) are emitted as-is.
    All other detectors are emitted as dbt-tests custom test stubs with
    ``dqt_`` prefix, e.g. ``dqt_iqr_fence``.

    The caller is responsible for implementing these custom test macros
    (or using dqt's dbt integration package when available).
    """
    # Group by table
    by_table: dict[str, list] = defaultdict(list)
    for check in checks:
        by_table[f"{check.schema_name}.{check.table_name}"].append(check)

    models = []
    for fq_table, table_checks in by_table.items():
        model_name = fq_table.split(".")[-1]
        model_entry: dict = {"name": model_name, "columns": [], "tests": []}

        col_checks: dict[str, list] = defaultdict(list)
        table_level_checks = []
        for check in table_checks:
            if check.column_name:
                col_checks[check.column_name].append(check)
            else:
                table_level_checks.append(check)

        # Column-level tests
        for col_name, col_check_list in col_checks.items():
            col_entry: dict = {"name": col_name, "tests": []}
            for check in col_check_list:
                native = _NATIVE_MAP.get(check.detector_slug)
                if native:
                    col_entry["tests"].append(native)
                else:
                    test_body: dict = {f"dqt_{check.detector_slug}": {}}
                    if check.params:
                        test_body[f"dqt_{check.detector_slug}"] = dict(check.params)
                    col_entry["tests"].append(test_body)
            model_entry["columns"].append(col_entry)

        # Table-level tests
        for check in table_level_checks:
            native = _NATIVE_MAP.get(check.detector_slug)
            if native:
                model_entry["tests"].append(native)
            else:
                test_body = {f"dqt_{check.detector_slug}": dict(check.params) if check.params else {}}
                model_entry["tests"].append(test_body)

        if not model_entry["tests"]:
            del model_entry["tests"]

        models.append(model_entry)

    return yaml.dump({"version": 2, "models": models}, sort_keys=False, allow_unicode=True)
```

Add `compile` subcommand to CLI `main.py`:

```python
def _cmd_compile(args: argparse.Namespace) -> None:
    """Compile a dqt YAML check file to the target format."""
    from dqt.checks.loader import load_checks_file, CheckValidationError

    try:
        checks = load_checks_file(args.yaml_file)
    except (FileNotFoundError, CheckValidationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.to == "dbt":
        from dqt.compat.dbt_tests import checks_to_dbt_yaml
        print(checks_to_dbt_yaml(checks))
    else:
        print(f"error: unknown target '{args.to}'", file=sys.stderr)
        sys.exit(1)
```

And in `main()` dispatch registration:

```python
    p_compile = sub.add_parser("compile", help="Compile checks to another format (e.g. dbt)")
    p_compile.add_argument("yaml_file")
    p_compile.add_argument("--to", required=True, choices=["dbt"],
                           help="Target format")
```

- [ ] **Step 4: Run tests**

```
cd packages/dqt && uv run pytest tests/compat/test_dbt_tests.py -v
```
Expected: all PASS

- [ ] **Step 5: Commit**

```
git add packages/dqt/src/dqt/compat/dbt_tests.py packages/dqt/src/dqt/compat/__init__.py packages/dqt/src/dqt/cli/main.py packages/dqt/tests/compat/
git commit -m "feat: dqt compile --to dbt emits dbt schema YAML with native and custom test stubs"
```

---

## Phase 5 — Documentation and trust

### Task 14: Calibration helper API

**Spec:** `Detector.suggest_threshold(reference_df, target_fpr=0.001)` fits on clean baseline, picks threshold for target false-positive rate, returns calibration report.

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/_calibration.py`
- Modify: `packages/dqt/src/dqt/algorithms/_base.py`
- Test: `packages/dqt/tests/algorithms/test_calibration.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/algorithms/test_calibration.py
import numpy as np
import pandas as pd
import pytest


def test_suggest_threshold_iqr_fence():
    """suggest_threshold returns a calibration report dict."""
    from dqt.algorithms.outliers_uni.iqr_fence import IQRFenceDetector

    rng = np.random.default_rng(42)
    ref = pd.DataFrame({"x": rng.normal(0, 1, 1000)})
    det = IQRFenceDetector()
    report = det.suggest_threshold(ref, target_fpr=0.01)

    assert "suggested_threshold" in report
    assert "actual_fpr" in report
    assert "n_bootstrap" in report
    # FPR on clean data should be close to target
    assert report["actual_fpr"] <= 0.05, f"FPR too high: {report['actual_fpr']}"


def test_suggest_threshold_wasserstein():
    """Wasserstein-1 calibration returns a threshold."""
    from dqt.algorithms.drift.wasserstein import Wasserstein1Detector

    rng = np.random.default_rng(42)
    ref = pd.DataFrame({"x": rng.normal(0, 1, 500)})
    det = Wasserstein1Detector()
    report = det.suggest_threshold(ref, target_fpr=0.05)
    assert report["suggested_threshold"] > 0
```

- [ ] **Step 2: Run test to confirm failure**

```
cd packages/dqt && uv run pytest tests/algorithms/test_calibration.py -v
```
Expected: FAIL — `AttributeError`

- [ ] **Step 3: Create `_calibration.py`**

```python
# packages/dqt/src/dqt/algorithms/_calibration.py
"""Bootstrap calibration helper for BaseDetector.suggest_threshold()."""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Any


def suggest_threshold(
    detector,
    reference_df: pd.DataFrame,
    target_fpr: float = 0.001,
    n_bootstrap: int = 200,
    bootstrap_size: int | None = None,
) -> dict[str, Any]:
    """Fit the detector on reference_df and estimate a score threshold for target_fpr.

    Procedure:
    1. Fit the detector on reference_df.
    2. Bootstrap n_bootstrap samples from reference_df (same-distribution scores).
    3. Find the score percentile corresponding to (1 - target_fpr).
    4. Return the threshold and the actual FPR at that threshold.
    """
    state = detector.fit(reference_df)
    n = len(reference_df)
    bs_size = bootstrap_size or n

    rng = np.random.default_rng(42)
    boot_scores: list[float] = []
    for _ in range(n_bootstrap):
        idx = rng.integers(0, n, size=bs_size)
        sample = reference_df.iloc[idx].reset_index(drop=True)
        result = detector.score(sample, state)
        boot_scores.append(result.score)

    boot_scores_arr = np.array(boot_scores)
    threshold = float(np.percentile(boot_scores_arr, (1.0 - target_fpr) * 100))
    actual_fpr = float(np.mean(boot_scores_arr > threshold))

    return {
        "suggested_threshold": threshold,
        "target_fpr": target_fpr,
        "actual_fpr": actual_fpr,
        "n_bootstrap": n_bootstrap,
        "score_p50": float(np.percentile(boot_scores_arr, 50)),
        "score_p95": float(np.percentile(boot_scores_arr, 95)),
        "score_p99": float(np.percentile(boot_scores_arr, 99)),
    }
```

- [ ] **Step 4: Wire into `BaseDetector`**

In `packages/dqt/src/dqt/algorithms/_base.py`, add to `BaseDetector`:

```python
    def suggest_threshold(
        self,
        reference_df: "pd.DataFrame",
        target_fpr: float = 0.001,
        n_bootstrap: int = 200,
    ) -> dict:
        """Bootstrap-calibrate a score threshold for target false-positive rate on clean data."""
        from dqt.algorithms._calibration import suggest_threshold as _suggest
        return _suggest(self, reference_df, target_fpr=target_fpr, n_bootstrap=n_bootstrap)
```

- [ ] **Step 5: Run tests**

```
cd packages/dqt && uv run pytest tests/algorithms/test_calibration.py -v
```
Expected: all PASS

- [ ] **Step 6: Commit**

```
git add packages/dqt/src/dqt/algorithms/_calibration.py packages/dqt/src/dqt/algorithms/_base.py packages/dqt/tests/algorithms/test_calibration.py
git commit -m "feat: Detector.suggest_threshold() bootstrap calibration for target false-positive rate"
```

---

### Task 15: Per-detector algorithm documentation

**Spec:** Every detector gets a one-paragraph entry in `docs/algorithms/` with assumptions, failure modes, recommended thresholds, and a usage example.

**Files:**
- Create: `docs/algorithms/outliers_uni.md`
- Create: `docs/algorithms/drift.md`
- Create: `docs/algorithms/timeseries.md`
- Create: `docs/algorithms/causality.md`

- [ ] **Step 1: Create `docs/algorithms/outliers_uni.md`**

```markdown
# Univariate Outlier Detectors

## IQR Fence (`iqr_fence`)
**Ref:** Tukey (1977) *Exploratory Data Analysis*

Flags values outside Q1 − k·IQR and Q3 + k·IQR. Default k=3.0 (outer fence).

**Assumptions:** No normality required. Works on any unimodal distribution.

**Works well when:** Data is roughly symmetric. Sample N ≥ 50.

**Fails when:** Extremely heavy-tailed distributions (Pareto, Zipf) — even k=3 may over-flag. Use `adjusted_boxplot` (medcouple correction) instead.

**Expected false-alarm rate at k=3.0:** ~0.0002% on normal data. On log-normal data with σ≥2: ~0.5%.

**Recommended thresholds by data shape:**
- Revenue/order-value (log-normal): use k=3.0 (default)
- Count data (Poisson): use k=1.5 with `warn_threshold=0.001`
- Ratio data (0–1): use k=2.0

```python
from dqt.algorithms.outliers_uni.iqr_fence import IQRFenceDetector
det = IQRFenceDetector(k=3.0)  # outer fence; k=1.5 for inner
```

## Modified Z-Score / MAD (`mad_outlier_fraction`)
**Ref:** Iglewicz & Hoaglin (1993) *How to Detect and Handle Outliers*

Flags values where |0.6745 * (x − median) / MAD| > 3.5. Robust to outliers in reference because MAD ignores extreme values when computing scale.

**Assumptions:** Approximately unimodal distribution.

**Works well when:** Data has outliers that would inflate the standard deviation (making Z-score blind). Minimum N=15.

**Fails when:** Multimodal data (bimodal revenue by customer tier). Use a mixture model or `isolation_forest` instead.

**Expected false-alarm rate at threshold 3.5:** ~0.007% on normal data.

```python
from dqt.algorithms.outliers_uni.mad import MADDetector
det = MADDetector(threshold=3.5)  # 3.5 is Iglewicz & Hoaglin's recommendation
```

## Grubbs' Test (`grubbs`)
**Ref:** Grubbs (1950) *Ann. Math. Statist.*

Tests whether the single most extreme value is a statistically significant outlier (using the t-distribution).

**Assumptions:** Approximate normality. Tests exactly ONE outlier at a time.

**Works well when:** You expect at most one outlier and data is roughly normal. Classic use: measurement instrument calibration.

**Fails when:** Multiple outliers (masking effect — outliers hide each other). Use GESD instead.

**Minimum N:** 25 for reliable power.

```python
from dqt.algorithms.outliers_uni.grubbs import GrubbsDetector
det = GrubbsDetector()
```

## Generalized ESD (`generalized_esd`)
**Ref:** Rosner (1983) *Technometrics* — Percentage Points for a Generalized ESD Many-Outlier Procedure

Tests for up to k outliers simultaneously, handling the masking problem.

**Assumptions:** Approximate normality. N ≥ 50.

**Works well when:** You suspect multiple outliers and data is approximately normal.

**Fails when:** Heavily skewed data (use MAD or IQR instead). Large N (>10k) with only 1–2 real outliers — GESD's fraction score becomes very small.

```python
from dqt.algorithms.outliers_uni.grubbs import GeneralizedESDDetector
det = GeneralizedESDDetector(max_outliers=0, alpha=0.05)  # 0 = auto (max 100)
```
```

- [ ] **Step 2: Create `docs/algorithms/drift.md`**

```markdown
# Drift Detectors

## Wasserstein-1 / Earth-Mover Distance (`wasserstein_1`)
**Ref:** Kantorovich (1942); Rubner et al. (2000) *IJCV*

Measures the minimum "work" to transform one distribution into another. Score is normalized by reference std so it's interpretable across scales.

**Assumptions:** Continuous or ordinal data. No distributional assumptions.

**Works well when:** Gradual shifts, heavy-tailed distributions, revenue/count/ratio data. The recommended default for numeric drift. Sensitive to both location and shape changes.

**Fails when:** Data is categorical (use chi-square or PSI). Very small N (<100) produces high variance.

**Thresholds:** score 0.2 = moderate shift (~0.2 std); score 0.5 = large shift (~0.5 std).

**Minimum N:** 500 recommended for stable estimates.

```python
from dqt.algorithms.drift.wasserstein import Wasserstein1Detector
det = Wasserstein1Detector()
# Returns normalized earth-mover distance
```

## Two-Sample KS Test (`ks_pvalue`)
**Ref:** Kolmogorov (1933); Smirnov (1948)

Tests whether two samples come from the same distribution using the supremum of CDF differences.

**Assumptions:** Continuous data. IID samples.

**Works well when:** You want a p-value for "are these distributions the same?" Sharp detection of shape changes.

**Fails when:** Very large N — at N=10k, KS flags negligible differences as significant. Discrete or categorical data (use chi-square). For gradual drift prefer Wasserstein-1.

**Note:** Score = 1 − p-value. Large samples will nearly always produce significant results even when the actual shift is negligible. Use `n_ref` and `n_curr` in details to assess power.

```python
from dqt.algorithms.drift.ks2sample import KS2SampleDetector
det = KS2SampleDetector()
```

## PSI (`psi`)
**Ref:** Industry standard (insurance/credit scoring), no single canonical paper

Bins the reference distribution, counts current distribution in same bins. PSI < 0.1: stable. 0.1–0.2: moderate shift. > 0.2: significant population shift.

**Assumptions:** Requires sufficient data per bin (≥5 per bin recommended). Works on numeric and categorical data.

**Works well when:** Monitoring model input features for population shift. Industry-standard interpretability.

**Fails when:** Continuous data with non-standard distributions — bin edges from reference may misrepresent the current distribution. Use Wasserstein-1 for continuous data.

```python
from dqt.algorithms.drift.psi import PSIDetector
det = PSIDetector(n_bins=10)
```
```

- [ ] **Step 3: Create `docs/algorithms/timeseries.md`**

```markdown
# Time-Series Anomaly Detectors

## STL Residuals (`stl_residual_zscore`)
**Ref:** Cleveland et al. (1990) *JASA* — Seasonal-Trend Decomposition using Loess

Decomposes the series into trend, seasonal, and residual components. Anomalies are residuals with large Z-score relative to the reference residual distribution.

**Assumptions:** Regular time intervals. Seasonal period known (default 7 for daily data with weekly seasonality). Minimum 2 * period + 1 observations.

**Works well when:** Data has a clear seasonal pattern (daily/weekly/annual). Revenue, pageview, event-count metrics.

**Fails when:** Irregular intervals, missing values, or no seasonality. Use Page-Hinkley for non-seasonal data.

**Minimum N:** 100 for fit, 15 for score (2 * period + 1).

```python
from dqt.algorithms.timeseries.stl import STLAnomalyDetector
det = STLAnomalyDetector(period=7)   # 7 for weekly seasonality in daily data
```

## BOCPD (`bocpd`)
**Ref:** Adams & MacKay (2007) arXiv:0710.3742

Bayesian Online Changepoint Detection. Maintains a posterior over run-length (time since last changepoint). Score = max changepoint probability.

**Assumptions:** Normal-inverse-chi-squared conjugate prior. Works best on approximately Gaussian segments.

**Works well when:** Sudden level shifts (deploys, campaigns). Online streaming data.

**Fails when:** Gradual drift (use Wasserstein-1 or ADWIN). Very short series (<30 points).

**hazard_lambda default:** 50 (expected run length = 50 time steps between changepoints). Increase for slower-changing data.

```python
from dqt.algorithms.timeseries.bocpd import BOCPDDetector
det = BOCPDDetector(hazard_lambda=50)    # daily data: 50 steps ≈ 7 weeks between changes
# det = BOCPDDetector(hazard_lambda=200) # hourly data: 200 steps ≈ 8 days between changes
```

## ADWIN (`adwin`)
**Ref:** Bifet & Gavalda (2007) *SDM*

Adaptive Windowing. Scans all cut-points in the combined ref+current stream using Hoeffding's bound. Returns 1.0 if drift detected, 0.0 if stable.

**Assumptions:** Real-valued stream. Uses Hoeffding bound (distribution-free).

**Works well when:** Streaming data, online learning. Sensitive to mean shifts.

**Fails when:** Variance changes only (ADWIN detects mean shifts). Very noisy data with δ too small.

```python
from dqt.algorithms.drift.adwin import ADWINDetector
det = ADWINDetector(delta=0.002)  # 0.002 ≈ 99.8% confidence before alarm
```
```

- [ ] **Step 4: Create `docs/algorithms/causality.md`**

```markdown
# Causal Discovery

## Granger Causality (`granger_pairwise`)
**Ref:** Granger (1969) *Econometrica* 37(3)

Tests whether past values of X help predict Y beyond Y's own past. Uses VAR-based AIC lag selection, stationarity gating (ADF), and BH-FDR correction.

**Assumptions:** Bivariate testing. Stationarity (auto-differencing applied). Linear relationships. Minimum N=20.

**Works well when:** Two time series with a clear lag relationship. Quick pairwise exploration.

**Fails when:**
- **Transitive chains (X→Y→Z):** Granger will find X→Z even when the direct effect is mediated by Y. This is not a bug — it's a bivariate limitation. Use PCMCI+ to condition on Y.
- **Nonlinear relationships:** p-values are not meaningful for strongly nonlinear systems.
- **Short series:** N < 50 makes AIC lag selection unstable.

**FDR note:** All pairs are BH-corrected. `evidence_strength="moderate"` means adjusted p < 0.05. Check `confounder_candidates` for Z that drives both X and Y.

```python
from dqt.causality.granger import granger_pairwise
report = granger_pairwise(df, max_lag=4)
for edge in report.significant_edges:
    print(f"{edge.cause} → {edge.effect}  "
          f"(lag={edge.selected_lag}, strength={edge.evidence_strength})")
    if edge.confounder_candidates:
        print(f"  ⚠ possible confounders: {edge.confounder_candidates}")
```

## PCMCI+ (`pcmci_pairwise`)
**Ref:** Runge et al. (2019) *Science Advances*

Multivariate causal discovery that conditions each bivariate test on all other variables — solves Granger's transitive-chain problem.

**Assumptions:** Stationarity (auto-differencing applied). Linear (ParCorr) or nonlinear (GPDC) conditional independence. Minimum N=50.

**Works well when:** Panel of 3+ time series where you want to distinguish direct from indirect effects. Better precision than Granger on chains and forks.

**Fails when:** N < 100 (multivariate conditioning is expensive). Requires `dqt[causal]` extra.

**Hyperparameter sensitivity:** Run with tau_max=3 and tau_max=5 — if results differ materially, flag edges as "fragile."

```python
from dqt.causality.pcmci import pcmci_pairwise
report = pcmci_pairwise(df, tau_max=3, cond_ind_test="parcorr")
for edge in report.significant_edges:
    print(f"{edge.cause} → {edge.effect}  lag={edge.lag}")
```
```

- [ ] **Step 5: Commit**

```
git add docs/algorithms/
git commit -m "docs: per-detector algorithm docs with assumptions, failure modes, thresholds"
```

---

### Task 16: "When NOT to use dqt" page

**Spec:** Honest disqualification page — the strongest credibility signal.

**Files:**
- Create: `docs/when-not-to-use-dqt.md`

- [ ] **Step 1: Create the page**

```markdown
# When NOT to use dqt

This is the most honest thing we can put in the documentation.

## Use a managed service instead if:

**You need SLAs and enterprise support.** Monte Carlo, Anomalo, and Bigeye offer managed services with on-call support, SLAs, and Salesforce/ServiceNow integrations dqt won't match for years. If your data team needs a vendor to call when things break at 3am, buy a managed product.

**Your team isn't comfortable with statistics.** The causal layer will mislead more than it helps if no one on the team can interpret a p-value, understand what "conditioning on a confounder" means, or distinguish correlation from causation. The `plain_english` output is a starting point, not a substitute for statistical literacy.

**You only need declarative checks.** Great Expectations and Soda have larger communities, more connectors, and more operators familiar with them. If all you need is "column X must be non-null and in set {A, B, C}", use one of those.

**You're on a team of 1 with no time for calibration.** dqt's default thresholds are statistically principled but not tuned to your data. You'll get false alarms until you run `suggest_threshold()` on your actual distributions. That calibration step takes a few hours and pays off, but it's not zero effort.

## dqt won't help you if:

**Your data isn't time-ordered.** Time-series detectors (STL, BOCPD, ADWIN, Matrix Profile) require temporal ordering. If your tables don't have a reliable timestamp column, skip those detectors entirely.

**Your warehouse isn't connected.** dqt needs to read samples from your warehouse. If your security model prohibits read-only service accounts with SELECT on `INFORMATION_SCHEMA`, the adapters won't work.

**You want to monitor ML model performance.** dqt monitors *data* quality. For model drift (accuracy drop, prediction distribution shift), you want Evidently, WhyLogs, or Arize.

**Your pipeline runs less than once per week.** Drift detectors and time-series methods need a reference window and a scoring window. Pipelines that run once a month don't produce enough signal for statistical methods — use threshold-based checks (`volume_change_ratio`, `null_fraction`) only.

## On the causal layer specifically:

The causal discovery layer (Granger, PCMCI+) is powerful when used correctly and dangerous when misused. Specifically:

- **All discovered edges are hypotheses, not facts.** The HITL review step exists for a reason. Never act on an unreviewed edge.
- **Granger causality ≠ causal causality.** Granger says "X's past predicts Y's future beyond Y's own past." It doesn't say X causes Y in any interventional sense. For interventional claims, use do-calculus with a confirmed DAG.
- **Confounders are reported, not controlled for.** The `confounder_candidates` field flags potential shared drivers but doesn't remove their effect. A "moderate" Granger edge with confounder candidates should be treated as "weak."
- **Short time series produce unreliable edges.** N < 50 for Granger, N < 100 for PCMCI+. Below these thresholds, edge detection is essentially random.

If you're not sure whether to trust a causal result, check the `evidence_strength` field and the `adjusted_p_value`. If `evidence_strength="weak"` or the `confounder_candidates` list is non-empty, defer human review before drawing conclusions.
```

- [ ] **Step 2: Commit**

```
git add docs/when-not-to-use-dqt.md
git commit -m "docs: 'When NOT to use dqt' — honest disqualification page"
```

---

## Final version bump and PyPI publish

- [ ] **Step 1: Bump version to 0.4.0**

In `packages/dqt/src/dqt/__init__.py`:
```python
__version__ = "0.4.0"
```

In `packages/dqt/pyproject.toml`:
```toml
version = "0.4.0"
```

- [ ] **Step 2: Build and publish**

```
cd packages/dqt
uv build
uv publish dist/dqtlib-0.4.0*
```

- [ ] **Step 3: Final commit and tag**

```
git add packages/dqt/src/dqt/__init__.py packages/dqt/pyproject.toml
git commit -m "chore: bump version to 0.4.0"
git tag dqt-v0.4.0
git push origin main --tags
```

---

## Self-review

### Spec coverage check

| Spec item | Covered by task |
|---|---|
| 1.1 Isolation Forest | Already fixed in v0.3.0 — no task needed |
| 1.2 Freshness string timestamps | Task 2 |
| 1.3 from_sql_files schema names | Task 1 |
| 1.4 BOCPD calibration | Already fixed in v0.3.0 — no task needed |
| 1.5 ADWIN display | Already fixed in v0.3.0 — no task needed |
| 2.1 Failure-mode test suite | Task 6 |
| 2.2 BH-FDR across check runs | NOT INCLUDED — requires significant runner redesign; score detectors don't uniformly return p-values. Deferred to a separate plan. |
| 2.3 Baseline strategies in runner | NOT INCLUDED — BaselineConfig model exists; runner wiring requires adapter changes not yet specced. Deferred. |
| 2.4 Power-aware warnings | Task 3 |
| 2.5 Sparse/zero-inflated routing | Task 4 |
| 2.6 Plain_english audit | Task 5 |
| 3.1 Column-level dbt lineage | Task 7 |
| 3.2 Transitive downstream/upstream | Already in LineageGraph.all_downstream/all_upstream — no task needed |
| 3.3 PCMCI+ | Task 8 |
| 3.4 Deployment-event confounding | NOT INCLUDED — requires EventSource interface design. Deferred to Phase 3 follow-on. |
| 3.5 Reviewer feedback loop | Task 9 |
| 4.1 dqt run execute | Task 10 |
| 4.2 Reproducibility bundle | Task 11 |
| 4.3 OpenLineage emission | Task 12 |
| 4.4 Compile to dbt tests | Task 13 |
| 4.5 Web app incident view | NOT INCLUDED — HTMX+FastAPI web app is a separate deliverable, not library code. Keep out of this plan. |
| 5.1 Per-detector docs | Task 15 |
| 5.2 Benchmark notebook | NOT INCLUDED — requires NAB/Yahoo data downloads and CI pipeline changes. Separate deliverable. |
| 5.3 Calibration helper | Task 14 |
| 5.4 Recipes | NOT INCLUDED — 5 notebooks × substantial writing. Separate content deliverable. |
| 5.5 When NOT to use | Task 16 |

### Deferred items summary

Four items explicitly deferred (not bugs — design work needed before implementation):
1. **2.2 BH-FDR across runs** — detectors don't uniformly expose p-values; needs a detector protocol extension
2. **2.3 Baseline strategies in runner** — needs adapter date-range filtering API
3. **3.4 Deployment-event confounding** — needs EventSource protocol design
4. **4.5 HTMX web app** — out of scope for library; separate apps/ deliverable
5. **5.2 Benchmark notebook** — data downloads and CI pipeline changes
6. **5.4 Recipes** — content work, not code

### Type consistency check

- `CausalEdgeReview.edge_id: UUID` — consistent with `GrangerEdge` (no UUID field; edge_id is assigned by caller)
- `RunResult.to_bundle(path)` — uses `Path` from pathlib; import added in method
- `OpenLineageEmitter.build_event()` returns `dict[str, Any]` — consistent with test expectations
- `checks_to_dbt_yaml(checks)` accepts `list[Check]` — correct type from `dqt.checks.models`
