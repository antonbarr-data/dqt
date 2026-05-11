# Group A Detectors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 10 missing Group A detectors (scipy/numpy only, no new deps) so the marketed slugs are actually registered and working.

**Architecture:** Each detector follows the `BaseDetector` contract: `fit(reference_df) → state`, `score(current_df, state) → DetectorResult`. Score is always a float in the range the STAT_SCALE defines. Verdict is computed via `self._verdict(score)` which reads from `STAT_SCALES`. New detectors are registered via `@registry.register` and auto-imported through their group's `__init__.py` → `dqt/__init__.py`.

**Tech Stack:** Python 3.12, numpy, scipy (already installed), pandas. No new dependencies.

---

## File Structure

**New implementation files:**
- `packages/dqt/src/dqt/algorithms/outliers_uni/iqr_fence.py` — IQR/Tukey fences
- `packages/dqt/src/dqt/algorithms/outliers_uni/grubbs.py` — Grubbs + Generalized ESD
- `packages/dqt/src/dqt/algorithms/drift/wasserstein.py` — Wasserstein-1
- `packages/dqt/src/dqt/algorithms/drift/psi.py` — Population Stability Index
- `packages/dqt/src/dqt/algorithms/drift/divergence.py` — KL + JS divergence
- `packages/dqt/src/dqt/algorithms/drift/chi_square.py` — Chi-square categorical drift
- `packages/dqt/src/dqt/algorithms/info/__init__.py` — new group
- `packages/dqt/src/dqt/algorithms/info/cramers_v.py` — Cramér's V
- `packages/dqt/src/dqt/algorithms/pattern/__init__.py` — new group
- `packages/dqt/src/dqt/algorithms/pattern/benford.py` — Benford's Law

**New test files:**
- `packages/dqt/tests/algorithms/outliers_uni/test_iqr_fence.py`
- `packages/dqt/tests/algorithms/outliers_uni/test_grubbs.py`
- `packages/dqt/tests/algorithms/drift/test_wasserstein.py`
- `packages/dqt/tests/algorithms/drift/test_psi.py`
- `packages/dqt/tests/algorithms/drift/test_divergence.py`
- `packages/dqt/tests/algorithms/drift/test_chi_square.py`
- `packages/dqt/tests/algorithms/info/__init__.py`
- `packages/dqt/tests/algorithms/info/test_cramers_v.py`
- `packages/dqt/tests/algorithms/pattern/__init__.py`
- `packages/dqt/tests/algorithms/pattern/test_benford.py`

**Modified files:**
- `packages/dqt/src/dqt/algorithms/_scales.py` — 10 new StatScale entries (Task 1)
- `packages/dqt/src/dqt/algorithms/outliers_uni/__init__.py` — add IQR, Grubbs, GESD imports
- `packages/dqt/src/dqt/algorithms/drift/__init__.py` — add Wasserstein, PSI, KL/JS, chi-square imports
- `packages/dqt/src/dqt/__init__.py` — add `import dqt.algorithms.info` and `import dqt.algorithms.pattern`
- `apps/web/src/app/page.tsx` — remove non-existent slugs from DETECTORS array (Task 9)

---

## Task 1: STAT_SCALES entries for all 10 new detectors

**Files:**
- Modify: `packages/dqt/src/dqt/algorithms/_scales.py`

- [ ] **Step 1: Add 10 new StatScale entries to STAT_SCALES**

Append inside the `STAT_SCALES` dict (before the closing `]`):

```python
        StatScale("iqr_fence",           0.20, 0.01,  0.05,  "lower_is_better", "Outlier fraction (IQR)",          "Fraction of values outside Tukey IQR fences; k=1.5 by default"),
        StatScale("grubbs",              1.0,  0.95,  0.99,  "lower_is_better", "Grubbs outlier (1−p)",            "1 − p-value from Grubbs test; warn p<0.05, fail p<0.01"),
        StatScale("generalized_esd",     0.10, 0.01,  0.05,  "lower_is_better", "Outlier fraction (GESD)",         "Fraction of outliers found by Generalized ESD (Rosner 1983)"),
        StatScale("wasserstein_1",       10.0, 0.20,  0.50,  "lower_is_better", "Wasserstein-1 (norm.)",           "Earth-mover distance normalized by reference std; 0.2=moderate shift, 0.5=large"),
        StatScale("psi",                 2.0,  0.10,  0.20,  "lower_is_better", "Population Stability Index",      "PSI<0.1 stable, 0.1–0.2 moderate shift, >0.2 significant population shift"),
        StatScale("kl_divergence",       5.0,  0.10,  0.30,  "lower_is_better", "KL divergence",                   "Kullback–Leibler divergence (binned); 0=identical distributions"),
        StatScale("js_divergence",       1.0,  0.10,  0.20,  "lower_is_better", "Jensen-Shannon distance",         "JS distance (bounded [0,1]); 0=identical, 1=maximally different"),
        StatScale("chi_square_drift",    1.0,  0.95,  0.99,  "lower_is_better", "Chi-square drift (1−p)",          "1 − p-value from chi-square test for categorical drift; warn p<0.05, fail p<0.01"),
        StatScale("cramers_v",           1.0,  0.15,  0.30,  "lower_is_better", "Cramér's V (drift)",              "V from 2×k contingency table; 0=no drift, 1=maximum categorical drift"),
        StatScale("benford_law_fit",     1.0,  0.95,  0.99,  "lower_is_better", "Benford's Law fit (1−p)",         "1 − p-value from chi-square vs expected first-digit frequencies"),
```

- [ ] **Step 2: Verify scales are importable**

```bash
cd c:\anton\dqt
uv run python -c "from dqt.algorithms._scales import STAT_SCALES; print(len(STAT_SCALES), 'scales')"
```
Expected output: `48 scales` (38 existing + 10 new)

- [ ] **Step 3: Commit**

```bash
git add packages/dqt/src/dqt/algorithms/_scales.py
git commit -m "feat(scales): add 10 STAT_SCALES entries for Group A detectors"
```

---

## Task 2: `iqr_fence` — IQR/Tukey fences

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/outliers_uni/iqr_fence.py`
- Create: `packages/dqt/tests/algorithms/outliers_uni/test_iqr_fence.py`
- Modify: `packages/dqt/src/dqt/algorithms/outliers_uni/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/algorithms/outliers_uni/test_iqr_fence.py
# Ref: Tukey (1977) Exploratory Data Analysis
import math
import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
import hypothesis.strategies as st
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.outliers_uni.iqr_fence import IQRFenceDetector
    return IQRFenceDetector()


def test_iqr_detects_spike(detector):
    rng = np.random.default_rng(42)
    data = rng.normal(0, 1, 99).tolist()
    data.append(200.0)
    df = pd.DataFrame({"value": data})
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.details["outlier_fraction"] > 0
    assert result.verdict != Verdict.pass_


def test_iqr_no_false_positives(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert result.verdict == Verdict.pass_


def test_iqr_many_outliers_fail(detector):
    rng = np.random.default_rng(7)
    clean = rng.normal(0, 1, 900)
    spikes = np.full(100, 500.0)
    df = pd.DataFrame({"value": np.concatenate([clean, spikes])})
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.verdict == Verdict.fail


def test_iqr_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.005, "iqr_fence") == Verdict.pass_
    assert compute_verdict(0.02, "iqr_fence") == Verdict.warn
    assert compute_verdict(0.08, "iqr_fence") == Verdict.fail


@given(
    values=st.lists(
        st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
        min_size=10, max_size=500,
    )
)
@settings(max_examples=100)
def test_iqr_stability(values):
    from dqt.algorithms.outliers_uni.iqr_fence import IQRFenceDetector
    df = pd.DataFrame({"value": values})
    det = IQRFenceDetector()
    state = det.fit(df)
    result = det.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)
```

- [ ] **Step 2: Run test — verify it fails**

```bash
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/outliers_uni/test_iqr_fence.py -v 2>&1 | Select-Object -Last 10
```
Expected: `ImportError` or `ModuleNotFoundError` for `iqr_fence`.

- [ ] **Step 3: Implement `iqr_fence.py`**

```python
# packages/dqt/src/dqt/algorithms/outliers_uni/iqr_fence.py
# Ref: Tukey (1977) Exploratory Data Analysis — inner fences Q1−k·IQR, Q3+k·IQR
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState
from dqt.algorithms._registry import registry


@registry.register
class IQRFenceDetector(BaseDetector):
    """Tukey IQR fence outlier detection. Score = fraction of values outside [Q1−k·IQR, Q3+k·IQR]."""
    slug = "iqr_fence"
    group = "outliers_uni"

    def __init__(self, k: float = 1.5) -> None:
        self._k = k

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        col = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        q1, q3 = float(np.percentile(col, 25)), float(np.percentile(col, 75))
        iqr = q3 - q1
        return {"lower": q1 - self._k * iqr, "upper": q3 + self._k * iqr}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        col = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        n = len(col)
        n_out = int(np.sum((col < state["lower"]) | (col > state["upper"])))
        frac = n_out / n if n > 0 else 0.0
        return DetectorResult(
            score=frac,
            verdict=self._verdict(frac),
            plain_english=(
                f"{frac:.1%} of values outside Tukey fences "
                f"[{state['lower']:.3g}, {state['upper']:.3g}]"
            ),
            details={
                "outlier_fraction": frac,
                "lower_fence": state["lower"],
                "upper_fence": state["upper"],
            },
        )
```

- [ ] **Step 4: Register in `outliers_uni/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/outliers_uni/__init__.py
from dqt.algorithms.outliers_uni.mad import DoubleMadOutlierDetector, MADOutlierDetector
from dqt.algorithms.outliers_uni.zscore import ZScoreDetector
from dqt.algorithms.outliers_uni.adjusted_boxplot import AdjustedBoxplotDetector
from dqt.algorithms.outliers_uni.auto_outlier import AutoOutlierDetector
from dqt.algorithms.outliers_uni.outlier_fraction_range import OutlierFractionRangeDetector
from dqt.algorithms.outliers_uni.iqr_fence import IQRFenceDetector

__all__ = [
    "MADOutlierDetector",
    "DoubleMadOutlierDetector",
    "ZScoreDetector",
    "AdjustedBoxplotDetector",
    "AutoOutlierDetector",
    "OutlierFractionRangeDetector",
    "IQRFenceDetector",
]
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/outliers_uni/test_iqr_fence.py -v 2>&1 | Select-Object -Last 10
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add packages/dqt/src/dqt/algorithms/outliers_uni/iqr_fence.py packages/dqt/src/dqt/algorithms/outliers_uni/__init__.py packages/dqt/tests/algorithms/outliers_uni/test_iqr_fence.py
git commit -m "feat(detectors): add iqr_fence — Tukey IQR fence outlier detection"
```

---

## Task 3: `grubbs` + `generalized_esd`

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/outliers_uni/grubbs.py`
- Create: `packages/dqt/tests/algorithms/outliers_uni/test_grubbs.py`
- Modify: `packages/dqt/src/dqt/algorithms/outliers_uni/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/algorithms/outliers_uni/test_grubbs.py
# Ref: Grubbs (1950) Ann. Math. Statist. — test for single outlier
# Ref: Rosner (1983) Technometrics — generalized ESD for up to k outliers
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def grubbs():
    from dqt.algorithms.outliers_uni.grubbs import GrubbsDetector
    return GrubbsDetector()


@pytest.fixture()
def gesd():
    from dqt.algorithms.outliers_uni.grubbs import GeneralizedESDDetector
    return GeneralizedESDDetector()


def test_grubbs_detects_spike(grubbs):
    rng = np.random.default_rng(42)
    data = rng.normal(0, 1, 50).tolist()
    data.append(15.0)
    df = pd.DataFrame({"value": data})
    state = grubbs.fit(df)
    result = grubbs.score(df, state)
    assert result.verdict != Verdict.pass_
    assert result.score > 0.95


def test_grubbs_no_false_positives(grubbs, normal_df):
    state = grubbs.fit(normal_df)
    result = grubbs.score(normal_df, state)
    assert result.verdict == Verdict.pass_


def test_grubbs_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.90, "grubbs") == Verdict.pass_
    assert compute_verdict(0.96, "grubbs") == Verdict.warn
    assert compute_verdict(0.995, "grubbs") == Verdict.fail


def test_gesd_detects_multiple_outliers(gesd):
    rng = np.random.default_rng(42)
    data = rng.normal(0, 1, 100).tolist()
    data.extend([20.0, -20.0, 25.0])
    df = pd.DataFrame({"value": data})
    state = gesd.fit(df)
    result = gesd.score(df, state)
    assert result.details["n_outliers"] >= 2
    assert result.verdict != Verdict.pass_


def test_gesd_no_false_positives(gesd, normal_df):
    state = gesd.fit(normal_df)
    result = gesd.score(normal_df, state)
    assert result.verdict == Verdict.pass_


def test_gesd_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.005, "generalized_esd") == Verdict.pass_
    assert compute_verdict(0.02, "generalized_esd") == Verdict.warn
    assert compute_verdict(0.08, "generalized_esd") == Verdict.fail


def test_grubbs_score_bounded():
    from dqt.algorithms.outliers_uni.grubbs import GrubbsDetector
    rng = np.random.default_rng(0)
    for _ in range(20):
        df = pd.DataFrame({"value": rng.normal(0, 1, 50)})
        det = GrubbsDetector()
        state = det.fit(df)
        result = det.score(df, state)
        assert 0.0 <= result.score <= 1.0
        assert not math.isnan(result.score)
```

- [ ] **Step 2: Run test — verify it fails**

```bash
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/outliers_uni/test_grubbs.py -v 2>&1 | Select-Object -Last 5
```
Expected: `ImportError` for `grubbs`.

- [ ] **Step 3: Implement `grubbs.py`**

```python
# packages/dqt/src/dqt/algorithms/outliers_uni/grubbs.py
# Ref: Grubbs (1950) Ann. Math. Statist. — outlier test using max |xi-x̄|/s
# Ref: Rosner (1983) Technometrics — generalized ESD for up to k outliers
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry


def _grubbs_p_value(values: np.ndarray) -> float:
    """Return p-value for the Grubbs test (two-tailed)."""
    n = len(values)
    if n < 3:
        return 1.0
    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1))
    if std == 0.0:
        return 1.0
    G = float(np.max(np.abs(values - mean)) / std)
    denom = (n - 1) ** 2 - G ** 2 * n
    if denom <= 0:
        return 0.0
    t_stat = float(np.sqrt(G ** 2 * n * (n - 2) / denom))
    p_one = float(1.0 - stats.t.cdf(t_stat, df=n - 2))
    return float(min(2.0 * n * p_one, 1.0))


@registry.register
class GrubbsDetector(BaseDetector):
    """Grubbs' test for a single outlier. Score = 1 − p-value; warn p<0.05, fail p<0.01."""
    slug = "grubbs"
    group = "outliers_uni"

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        col = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        if len(col) < 3:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="Insufficient data for Grubbs test.",
                details={"p_value": 1.0},
            )
        p_value = _grubbs_p_value(col)
        score = float(1.0 - p_value)
        return DetectorResult(
            score=score,
            verdict=self._verdict(score),
            plain_english=(
                f"Grubbs test p={p_value:.4f} — "
                f"{'outlier detected' if score > 0.95 else 'no outlier detected'}"
            ),
            details={"p_value": p_value},
        )


def _gesd_n_outliers(values: np.ndarray, max_outliers: int, alpha: float = 0.05) -> int:
    """Rosner's Generalized ESD. Returns the number of outliers found."""
    n = len(values)
    work = values.copy().astype(float)
    n_found = 0
    for i in range(1, max_outliers + 1):
        if len(work) < 3:
            break
        mean = float(np.mean(work))
        std = float(np.std(work, ddof=1))
        if std == 0.0:
            break
        idx = int(np.argmax(np.abs(work - mean)))
        R = float(abs(work[idx] - mean) / std)
        m = len(work)
        p = alpha / (2.0 * (n - i + 1))
        t_crit = float(stats.t.ppf(1.0 - p, df=m - 2))
        lam = float((m - 1) * t_crit / np.sqrt(m * ((m - 2) + t_crit ** 2)))
        if R > lam:
            n_found = i
        work = np.delete(work, idx)
    return n_found


@registry.register
class GeneralizedESDDetector(BaseDetector):
    """Rosner Generalized ESD test for up to max_outliers outliers. Score = outlier fraction."""
    slug = "generalized_esd"
    group = "outliers_uni"

    def __init__(self, max_outliers: int = 0, alpha: float = 0.05) -> None:
        self._max_outliers = max_outliers  # 0 = auto: max(10, 10% of n)
        self._alpha = alpha

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        col = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        n = len(col)
        if n < 6:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="Insufficient data for GESD test (need ≥ 6 values).",
                details={"n_outliers": 0, "n": n},
            )
        max_k = self._max_outliers if self._max_outliers > 0 else max(10, n // 10)
        n_out = _gesd_n_outliers(col, max_outliers=max_k, alpha=self._alpha)
        frac = n_out / n
        return DetectorResult(
            score=frac,
            verdict=self._verdict(frac),
            plain_english=f"GESD found {n_out} outlier{'s' if n_out != 1 else ''} ({frac:.1%} of {n} values)",
            details={"n_outliers": n_out, "n": n, "max_k_tested": max_k},
        )
```

- [ ] **Step 4: Register in `outliers_uni/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/outliers_uni/__init__.py
from dqt.algorithms.outliers_uni.mad import DoubleMadOutlierDetector, MADOutlierDetector
from dqt.algorithms.outliers_uni.zscore import ZScoreDetector
from dqt.algorithms.outliers_uni.adjusted_boxplot import AdjustedBoxplotDetector
from dqt.algorithms.outliers_uni.auto_outlier import AutoOutlierDetector
from dqt.algorithms.outliers_uni.outlier_fraction_range import OutlierFractionRangeDetector
from dqt.algorithms.outliers_uni.iqr_fence import IQRFenceDetector
from dqt.algorithms.outliers_uni.grubbs import GrubbsDetector, GeneralizedESDDetector

__all__ = [
    "MADOutlierDetector",
    "DoubleMadOutlierDetector",
    "ZScoreDetector",
    "AdjustedBoxplotDetector",
    "AutoOutlierDetector",
    "OutlierFractionRangeDetector",
    "IQRFenceDetector",
    "GrubbsDetector",
    "GeneralizedESDDetector",
]
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/outliers_uni/test_grubbs.py -v 2>&1 | Select-Object -Last 10
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add packages/dqt/src/dqt/algorithms/outliers_uni/grubbs.py packages/dqt/src/dqt/algorithms/outliers_uni/__init__.py packages/dqt/tests/algorithms/outliers_uni/test_grubbs.py
git commit -m "feat(detectors): add grubbs + generalized_esd outlier tests"
```

---

## Task 4: `wasserstein_1` — Earth-mover distance

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/drift/wasserstein.py`
- Create: `packages/dqt/tests/algorithms/drift/test_wasserstein.py`
- Modify: `packages/dqt/src/dqt/algorithms/drift/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/algorithms/drift/test_wasserstein.py
# Ref: Wasserstein (1969); Kantorovich (1942) — earth-mover distance
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.drift.wasserstein import Wasserstein1Detector
    return Wasserstein1Detector()


def test_wasserstein_same_distribution_pass(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert result.verdict == Verdict.pass_
    assert result.score < 0.20


def test_wasserstein_large_shift_fail(detector, normal_df, shifted_df):
    state = detector.fit(normal_df)
    result = detector.score(shifted_df, state)
    assert result.verdict == Verdict.fail
    assert result.score > 0.50


def test_wasserstein_score_bounded(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert 0.0 <= result.score
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_wasserstein_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.05, "wasserstein_1") == Verdict.pass_
    assert compute_verdict(0.30, "wasserstein_1") == Verdict.warn
    assert compute_verdict(0.70, "wasserstein_1") == Verdict.fail


def test_wasserstein_details_present(detector, normal_df, shifted_df):
    state = detector.fit(normal_df)
    result = detector.score(shifted_df, state)
    assert "raw_distance" in result.details
    assert "ref_std" in result.details
```

- [ ] **Step 2: Run test — verify it fails**

```bash
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/drift/test_wasserstein.py -v 2>&1 | Select-Object -Last 5
```

- [ ] **Step 3: Implement `wasserstein.py`**

```python
# packages/dqt/src/dqt/algorithms/drift/wasserstein.py
# Ref: Kantorovich (1942); Wasserstein (1969) — 1-Wasserstein (earth-mover) distance
# Score = wasserstein_distance(ref, curr) / std(ref); dimensionless shift in units of σ
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_EPSILON = 1e-8


@registry.register
class Wasserstein1Detector(BaseDetector):
    """Wasserstein-1 (earth-mover) distance for distribution drift. Score normalised by reference std."""
    slug = "wasserstein_1"
    group = "drift"

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        col = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        return {"reference": col, "ref_std": max(float(np.std(col, ddof=1)), _EPSILON)}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        if len(curr) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"raw_distance": 0.0, "ref_std": state["ref_std"]},
            )
        raw = float(stats.wasserstein_distance(state["reference"], curr))
        score = raw / state["ref_std"]
        return DetectorResult(
            score=score,
            verdict=self._verdict(score),
            plain_english=(
                f"Wasserstein-1 distance = {raw:.4g} "
                f"({score:.2f}σ of reference); "
                f"{'drift detected' if score >= 0.20 else 'stable'}"
            ),
            details={"raw_distance": raw, "ref_std": state["ref_std"]},
        )
```

- [ ] **Step 4: Update `drift/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/drift/__init__.py
from dqt.algorithms.drift.ks2sample import KS2SampleDetector
from dqt.algorithms.drift.wasserstein import Wasserstein1Detector

__all__ = ["KS2SampleDetector", "Wasserstein1Detector"]
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/drift/test_wasserstein.py -v 2>&1 | Select-Object -Last 10
```

- [ ] **Step 6: Commit**

```bash
git add packages/dqt/src/dqt/algorithms/drift/wasserstein.py packages/dqt/src/dqt/algorithms/drift/__init__.py packages/dqt/tests/algorithms/drift/test_wasserstein.py
git commit -m "feat(detectors): add wasserstein_1 — earth-mover distance drift detector"
```

---

## Task 5: `psi` — Population Stability Index

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/drift/psi.py`
- Create: `packages/dqt/tests/algorithms/drift/test_psi.py`
- Modify: `packages/dqt/src/dqt/algorithms/drift/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/algorithms/drift/test_psi.py
# Ref: PSI (credit risk industry standard) — symmetric KL divergence over equal-frequency bins
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.drift.psi import PSIDetector
    return PSIDetector()


def test_psi_same_distribution_pass(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert result.verdict == Verdict.pass_
    assert result.score < 0.10


def test_psi_large_shift_fail(detector, normal_df, shifted_df):
    state = detector.fit(normal_df)
    result = detector.score(shifted_df, state)
    assert result.verdict == Verdict.fail
    assert result.score > 0.20


def test_psi_score_non_negative(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert result.score >= 0.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_psi_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.05, "psi") == Verdict.pass_
    assert compute_verdict(0.15, "psi") == Verdict.warn
    assert compute_verdict(0.25, "psi") == Verdict.fail


def test_psi_details_present(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert "n_bins" in result.details
    assert "psi" in result.details
```

- [ ] **Step 2: Run test — verify it fails**

```bash
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/drift/test_psi.py -v 2>&1 | Select-Object -Last 5
```

- [ ] **Step 3: Implement `psi.py`**

```python
# packages/dqt/src/dqt/algorithms/drift/psi.py
# Ref: PSI (Population Stability Index) — credit risk industry standard
# PSI = Σ (actual_% − expected_%) × ln(actual_% / expected_%)
# Thresholds: <0.1 stable, 0.1–0.2 moderate shift, >0.2 significant shift
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_EPSILON = 1e-6


@registry.register
class PSIDetector(BaseDetector):
    """Population Stability Index drift detector. Score = PSI value."""
    slug = "psi"
    group = "drift"

    def __init__(self, n_bins: int = 10) -> None:
        self._n_bins = n_bins

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        col = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        bin_edges = np.histogram_bin_edges(col, bins=self._n_bins)
        ref_counts, _ = np.histogram(col, bins=bin_edges)
        ref_frac = (ref_counts + _EPSILON) / (len(col) + self._n_bins * _EPSILON)
        return {"bin_edges": bin_edges, "ref_frac": ref_frac, "n_bins": self._n_bins}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        if len(curr) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"psi": 0.0, "n_bins": state["n_bins"]},
            )
        cur_counts, _ = np.histogram(curr, bins=state["bin_edges"])
        cur_frac = (cur_counts + _EPSILON) / (len(curr) + state["n_bins"] * _EPSILON)
        psi = float(np.sum((cur_frac - state["ref_frac"]) * np.log(cur_frac / state["ref_frac"])))
        psi = max(0.0, psi)
        verdict_label = (
            "significant population shift" if psi > 0.20
            else "moderate shift" if psi > 0.10
            else "stable"
        )
        return DetectorResult(
            score=psi,
            verdict=self._verdict(psi),
            plain_english=f"PSI = {psi:.4f} — {verdict_label}",
            details={"psi": psi, "n_bins": state["n_bins"]},
        )
```

- [ ] **Step 4: Update `drift/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/drift/__init__.py
from dqt.algorithms.drift.ks2sample import KS2SampleDetector
from dqt.algorithms.drift.wasserstein import Wasserstein1Detector
from dqt.algorithms.drift.psi import PSIDetector

__all__ = ["KS2SampleDetector", "Wasserstein1Detector", "PSIDetector"]
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/drift/test_psi.py -v 2>&1 | Select-Object -Last 10
```

- [ ] **Step 6: Commit**

```bash
git add packages/dqt/src/dqt/algorithms/drift/psi.py packages/dqt/src/dqt/algorithms/drift/__init__.py packages/dqt/tests/algorithms/drift/test_psi.py
git commit -m "feat(detectors): add psi — Population Stability Index drift detector"
```

---

## Task 6: `kl_divergence` + `js_divergence`

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/drift/divergence.py`
- Create: `packages/dqt/tests/algorithms/drift/test_divergence.py`
- Modify: `packages/dqt/src/dqt/algorithms/drift/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/algorithms/drift/test_divergence.py
# Ref: Kullback & Leibler (1951) Ann. Math. Statist.
# Ref: Lin (1991) IEEE Trans. Inf. Theory — Jensen-Shannon divergence
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def kl():
    from dqt.algorithms.drift.divergence import KLDivergenceDetector
    return KLDivergenceDetector()


@pytest.fixture()
def js():
    from dqt.algorithms.drift.divergence import JSDivergenceDetector
    return JSDivergenceDetector()


def test_kl_same_distribution_pass(kl, normal_df):
    state = kl.fit(normal_df)
    result = kl.score(normal_df, state)
    assert result.verdict == Verdict.pass_
    assert result.score < 0.10


def test_kl_large_shift_fail(kl, normal_df, shifted_df):
    state = kl.fit(normal_df)
    result = kl.score(shifted_df, state)
    assert result.verdict != Verdict.pass_


def test_kl_score_non_negative(kl, normal_df):
    state = kl.fit(normal_df)
    result = kl.score(normal_df, state)
    assert result.score >= 0.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_kl_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.05, "kl_divergence") == Verdict.pass_
    assert compute_verdict(0.15, "kl_divergence") == Verdict.warn
    assert compute_verdict(0.40, "kl_divergence") == Verdict.fail


def test_js_same_distribution_pass(js, normal_df):
    state = js.fit(normal_df)
    result = js.score(normal_df, state)
    assert result.verdict == Verdict.pass_
    assert result.score < 0.10


def test_js_bounded(js, normal_df, shifted_df):
    state = js.fit(normal_df)
    result = js.score(shifted_df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)


def test_js_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.05, "js_divergence") == Verdict.pass_
    assert compute_verdict(0.12, "js_divergence") == Verdict.warn
    assert compute_verdict(0.25, "js_divergence") == Verdict.fail
```

- [ ] **Step 2: Run test — verify it fails**

```bash
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/drift/test_divergence.py -v 2>&1 | Select-Object -Last 5
```

- [ ] **Step 3: Implement `divergence.py`**

```python
# packages/dqt/src/dqt/algorithms/drift/divergence.py
# Ref: Kullback & Leibler (1951) Ann. Math. Statist. — KL divergence
# Ref: Lin (1991) IEEE Trans. Inf. Theory — Jensen-Shannon divergence
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.spatial.distance import jensenshannon

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_EPSILON = 1e-8


def _histogram_probs(col: np.ndarray, bin_edges: np.ndarray) -> np.ndarray:
    counts, _ = np.histogram(col, bins=bin_edges)
    probs = counts + _EPSILON
    return probs / probs.sum()


@registry.register
class KLDivergenceDetector(BaseDetector):
    """KL divergence drift detector (binned). Score = KL(current ‖ reference)."""
    slug = "kl_divergence"
    group = "drift"

    def __init__(self, n_bins: int = 10) -> None:
        self._n_bins = n_bins

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        col = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        bin_edges = np.histogram_bin_edges(col, bins=self._n_bins)
        ref_probs = _histogram_probs(col, bin_edges)
        return {"bin_edges": bin_edges, "ref_probs": ref_probs}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        if len(curr) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"kl_divergence": 0.0},
            )
        cur_probs = _histogram_probs(curr, state["bin_edges"])
        kl = float(np.sum(cur_probs * np.log(cur_probs / state["ref_probs"])))
        kl = max(0.0, kl)
        return DetectorResult(
            score=kl,
            verdict=self._verdict(kl),
            plain_english=f"KL divergence = {kl:.4f} — {'drift detected' if kl >= 0.10 else 'stable'}",
            details={"kl_divergence": kl},
        )


@registry.register
class JSDivergenceDetector(BaseDetector):
    """Jensen-Shannon distance drift detector (binned, bounded [0,1])."""
    slug = "js_divergence"
    group = "drift"

    def __init__(self, n_bins: int = 10) -> None:
        self._n_bins = n_bins

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        col = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        bin_edges = np.histogram_bin_edges(col, bins=self._n_bins)
        ref_probs = _histogram_probs(col, bin_edges)
        return {"bin_edges": bin_edges, "ref_probs": ref_probs}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        if len(curr) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"js_distance": 0.0},
            )
        cur_probs = _histogram_probs(curr, state["bin_edges"])
        js = float(jensenshannon(state["ref_probs"], cur_probs))
        js = min(max(js, 0.0), 1.0)
        return DetectorResult(
            score=js,
            verdict=self._verdict(js),
            plain_english=f"JS distance = {js:.4f} — {'drift detected' if js >= 0.10 else 'stable'}",
            details={"js_distance": js},
        )
```

- [ ] **Step 4: Update `drift/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/drift/__init__.py
from dqt.algorithms.drift.ks2sample import KS2SampleDetector
from dqt.algorithms.drift.wasserstein import Wasserstein1Detector
from dqt.algorithms.drift.psi import PSIDetector
from dqt.algorithms.drift.divergence import KLDivergenceDetector, JSDivergenceDetector

__all__ = [
    "KS2SampleDetector",
    "Wasserstein1Detector",
    "PSIDetector",
    "KLDivergenceDetector",
    "JSDivergenceDetector",
]
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/drift/test_divergence.py -v 2>&1 | Select-Object -Last 10
```

- [ ] **Step 6: Commit**

```bash
git add packages/dqt/src/dqt/algorithms/drift/divergence.py packages/dqt/src/dqt/algorithms/drift/__init__.py packages/dqt/tests/algorithms/drift/test_divergence.py
git commit -m "feat(detectors): add kl_divergence + js_divergence drift detectors"
```

---

## Task 7: `chi_square_drift` — Categorical distribution drift

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/drift/chi_square.py`
- Create: `packages/dqt/tests/algorithms/drift/test_chi_square.py`
- Modify: `packages/dqt/src/dqt/algorithms/drift/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/algorithms/drift/test_chi_square.py
# Ref: Pearson (1900) Philosophical Magazine — chi-square goodness-of-fit test
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.drift.chi_square import ChiSquareDriftDetector
    return ChiSquareDriftDetector()


def _cat_df(categories, counts):
    vals = []
    for cat, n in zip(categories, counts):
        vals.extend([cat] * n)
    return pd.DataFrame({"value": vals})


def test_chi_square_same_distribution_pass(detector):
    ref = _cat_df(["a", "b", "c"], [400, 350, 250])
    curr = _cat_df(["a", "b", "c"], [410, 340, 250])
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.verdict == Verdict.pass_


def test_chi_square_large_shift_fail(detector):
    ref = _cat_df(["a", "b", "c"], [400, 350, 250])
    curr = _cat_df(["a", "b", "c"], [50, 50, 900])
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.verdict == Verdict.fail
    assert result.details["p_value"] < 0.01


def test_chi_square_score_bounded(detector):
    ref = _cat_df(["x", "y"], [500, 500])
    state = detector.fit(ref)
    result = detector.score(ref, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)


def test_chi_square_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.90, "chi_square_drift") == Verdict.pass_
    assert compute_verdict(0.96, "chi_square_drift") == Verdict.warn
    assert compute_verdict(0.995, "chi_square_drift") == Verdict.fail
```

- [ ] **Step 2: Run test — verify it fails**

```bash
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/drift/test_chi_square.py -v 2>&1 | Select-Object -Last 5
```

- [ ] **Step 3: Implement `chi_square.py`**

```python
# packages/dqt/src/dqt/algorithms/drift/chi_square.py
# Ref: Pearson (1900) Philosophical Magazine — chi-square goodness-of-fit test for categorical drift
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry


@registry.register
class ChiSquareDriftDetector(BaseDetector):
    """Chi-square test for categorical distribution drift. Score = 1 − p-value."""
    slug = "chi_square_drift"
    group = "drift"

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        col = reference.iloc[:, 0].dropna().astype(str)
        counts = col.value_counts()
        total = len(col)
        expected_frac = {cat: cnt / total for cat, cnt in counts.items()}
        return {"expected_frac": expected_frac, "categories": list(counts.index)}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr = current.iloc[:, 0].dropna().astype(str)
        if len(curr) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"p_value": 1.0},
            )
        n = len(curr)
        categories = state["categories"]
        curr_counts = curr.value_counts()
        observed = np.array([curr_counts.get(cat, 0) for cat in categories], dtype=float)
        expected = np.array([state["expected_frac"][cat] * n for cat in categories], dtype=float)
        # Drop zero-expected bins to avoid division by zero
        mask = expected > 0
        observed, expected = observed[mask], expected[mask]
        if len(observed) < 2:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="Insufficient categories for chi-square test.",
                details={"p_value": 1.0},
            )
        _, p_value = stats.chisquare(observed, f_exp=expected)
        score = float(1.0 - p_value)
        return DetectorResult(
            score=score,
            verdict=self._verdict(score),
            plain_english=(
                f"Chi-square test p={p_value:.4f} — "
                f"{'categorical drift detected' if score > 0.95 else 'stable'}"
            ),
            details={"p_value": float(p_value), "chi2_statistic": float(np.sum((observed - expected) ** 2 / expected))},
        )
```

- [ ] **Step 4: Update `drift/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/drift/__init__.py
from dqt.algorithms.drift.ks2sample import KS2SampleDetector
from dqt.algorithms.drift.wasserstein import Wasserstein1Detector
from dqt.algorithms.drift.psi import PSIDetector
from dqt.algorithms.drift.divergence import KLDivergenceDetector, JSDivergenceDetector
from dqt.algorithms.drift.chi_square import ChiSquareDriftDetector

__all__ = [
    "KS2SampleDetector",
    "Wasserstein1Detector",
    "PSIDetector",
    "KLDivergenceDetector",
    "JSDivergenceDetector",
    "ChiSquareDriftDetector",
]
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/drift/test_chi_square.py -v 2>&1 | Select-Object -Last 10
```

- [ ] **Step 6: Commit**

```bash
git add packages/dqt/src/dqt/algorithms/drift/chi_square.py packages/dqt/src/dqt/algorithms/drift/__init__.py packages/dqt/tests/algorithms/drift/test_chi_square.py
git commit -m "feat(detectors): add chi_square_drift — categorical distribution drift test"
```

---

## Task 8: `cramers_v` — Cramér's V categorical drift (new `info` group)

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/info/__init__.py`
- Create: `packages/dqt/src/dqt/algorithms/info/cramers_v.py`
- Create: `packages/dqt/tests/algorithms/info/__init__.py`
- Create: `packages/dqt/tests/algorithms/info/test_cramers_v.py`
- Modify: `packages/dqt/src/dqt/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/algorithms/info/test_cramers_v.py
# Ref: Cramér (1946) Mathematical Methods of Statistics — normalized chi-square association
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.info.cramers_v import CramersVDetector
    return CramersVDetector()


def _cat_df(categories, counts):
    vals = []
    for cat, n in zip(categories, counts):
        vals.extend([cat] * n)
    return pd.DataFrame({"value": vals})


def test_cramers_v_identical_distributions_pass(detector):
    ref = _cat_df(["a", "b", "c"], [400, 350, 250])
    state = detector.fit(ref)
    result = detector.score(ref, state)
    assert result.verdict == Verdict.pass_
    assert result.score < 0.10


def test_cramers_v_large_shift_fail(detector):
    ref = _cat_df(["a", "b", "c"], [400, 350, 250])
    curr = _cat_df(["a", "b", "c"], [50, 50, 900])
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.verdict == Verdict.fail
    assert result.score > 0.30


def test_cramers_v_bounded(detector):
    ref = _cat_df(["x", "y", "z"], [300, 400, 300])
    curr = _cat_df(["x", "y", "z"], [100, 700, 200])
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)


def test_cramers_v_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.05, "cramers_v") == Verdict.pass_
    assert compute_verdict(0.20, "cramers_v") == Verdict.warn
    assert compute_verdict(0.40, "cramers_v") == Verdict.fail
```

- [ ] **Step 2: Run test — verify it fails**

```bash
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/info/test_cramers_v.py -v 2>&1 | Select-Object -Last 5
```

- [ ] **Step 3: Implement `cramers_v.py`**

```python
# packages/dqt/src/dqt/algorithms/info/cramers_v.py
# Ref: Cramér (1946) Mathematical Methods of Statistics
# V = sqrt(χ² / (n · min(r−1, c−1))); for drift: 2-period × K-category contingency table
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry


@registry.register
class CramersVDetector(BaseDetector):
    """Cramér's V categorical drift. Builds 2×K contingency (reference vs current). Score = V."""
    slug = "cramers_v"
    group = "info"

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        col = reference.iloc[:, 0].dropna().astype(str)
        counts = col.value_counts()
        return {"ref_counts": counts.to_dict(), "categories": list(counts.index)}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr = current.iloc[:, 0].dropna().astype(str)
        if len(curr) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"cramers_v": 0.0},
            )
        categories = state["categories"]
        curr_counts = curr.value_counts().to_dict()
        row_ref = np.array([state["ref_counts"].get(c, 0) for c in categories], dtype=float)
        row_cur = np.array([curr_counts.get(c, 0) for c in categories], dtype=float)
        contingency = np.vstack([row_ref, row_cur])
        chi2, _, _, _ = stats.chi2_contingency(contingency, correction=False)
        n = contingency.sum()
        k = len(categories)
        if n == 0 or k < 2:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="Insufficient data for Cramér's V.",
                details={"cramers_v": 0.0},
            )
        v = float(np.sqrt(chi2 / (n * (min(2, k) - 1))))
        v = min(max(v, 0.0), 1.0)
        return DetectorResult(
            score=v,
            verdict=self._verdict(v),
            plain_english=f"Cramér's V = {v:.4f} — {'categorical drift' if v >= 0.15 else 'stable'}",
            details={"cramers_v": v, "chi2": float(chi2), "n": float(n)},
        )
```

- [ ] **Step 4: Create `info/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/info/__init__.py
from dqt.algorithms.info.cramers_v import CramersVDetector

__all__ = ["CramersVDetector"]
```

- [ ] **Step 5: Create empty test `__init__.py`**

Create an empty file: `packages/dqt/tests/algorithms/info/__init__.py`

- [ ] **Step 6: Wire into `dqt/__init__.py`**

Add after the existing group imports:

```python
import dqt.algorithms.info          # noqa: F401
```

- [ ] **Step 7: Run tests — verify they pass**

```bash
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/info/test_cramers_v.py -v 2>&1 | Select-Object -Last 10
```

- [ ] **Step 8: Commit**

```bash
git add packages/dqt/src/dqt/algorithms/info/ packages/dqt/src/dqt/__init__.py packages/dqt/tests/algorithms/info/
git commit -m "feat(detectors): add cramers_v — categorical drift via Cramér's V (new info group)"
```

---

## Task 9: `benford_law_fit` — Benford's Law (new `pattern` group)

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/pattern/__init__.py`
- Create: `packages/dqt/src/dqt/algorithms/pattern/benford.py`
- Create: `packages/dqt/tests/algorithms/pattern/__init__.py`
- Create: `packages/dqt/tests/algorithms/pattern/test_benford.py`
- Modify: `packages/dqt/src/dqt/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/algorithms/pattern/test_benford.py
# Ref: Benford (1938) Proc. Am. Philos. Soc. — first-digit law for naturally occurring numbers
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.pattern.benford import BenfordDetector
    return BenfordDetector()


def _benford_sample(n: int, seed: int = 42) -> pd.DataFrame:
    """Generate data that follows Benford's Law (log-uniform)."""
    rng = np.random.default_rng(seed)
    vals = 10 ** rng.uniform(0, 4, n)
    return pd.DataFrame({"value": vals})


def _uniform_first_digits(n: int) -> pd.DataFrame:
    """Generate data with uniform first digits — strongly violates Benford's."""
    rng = np.random.default_rng(99)
    # Each digit 1-9 equally likely as first digit
    first_digits = rng.integers(1, 10, n)
    rest = rng.uniform(0, 1, n)
    vals = (first_digits + rest).astype(float)
    return pd.DataFrame({"value": vals})


def test_benford_conforming_data_pass(detector):
    df = _benford_sample(5000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.verdict == Verdict.pass_
    assert result.score < 0.95


def test_benford_violation_detected(detector):
    df_benford = _benford_sample(5000)
    df_uniform = _uniform_first_digits(5000)
    state = detector.fit(df_benford)
    result = detector.score(df_uniform, state)
    assert result.verdict != Verdict.pass_
    assert result.details["p_value"] < 0.05


def test_benford_score_bounded(detector):
    df = _benford_sample(1000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)


def test_benford_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.90, "benford_law_fit") == Verdict.pass_
    assert compute_verdict(0.96, "benford_law_fit") == Verdict.warn
    assert compute_verdict(0.995, "benford_law_fit") == Verdict.fail


def test_benford_details_present(detector):
    df = _benford_sample(2000)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert "p_value" in result.details
    assert "chi2_statistic" in result.details
    assert "digit_fractions" in result.details
```

- [ ] **Step 2: Run test — verify it fails**

```bash
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/pattern/test_benford.py -v 2>&1 | Select-Object -Last 5
```

- [ ] **Step 3: Implement `benford.py`**

```python
# packages/dqt/src/dqt/algorithms/pattern/benford.py
# Ref: Benford (1938) Proc. Am. Philos. Soc. — first-digit law: P(d) = log10(1 + 1/d)
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

# Benford's expected first-digit probabilities for digits 1..9
_BENFORD_EXPECTED = np.array(
    [np.log10(1.0 + 1.0 / d) for d in range(1, 10)], dtype=float
)


def _first_digits(col: np.ndarray) -> np.ndarray:
    """Extract first significant digit (1–9) from each value."""
    abs_vals = np.abs(col[col != 0])
    if len(abs_vals) == 0:
        return np.array([], dtype=int)
    magnitudes = np.floor(np.log10(abs_vals))
    normalized = abs_vals / (10.0 ** magnitudes)
    return np.floor(normalized).astype(int)


@registry.register
class BenfordDetector(BaseDetector):
    """Benford's Law fit test. Score = 1 − p-value from chi-square vs expected first-digit frequencies."""
    slug = "benford_law_fit"
    group = "pattern"

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        col = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        digits = _first_digits(col)
        if len(digits) < 30:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="Insufficient data for Benford's Law test (need ≥ 30 non-zero values).",
                details={"p_value": 1.0, "chi2_statistic": 0.0, "digit_fractions": []},
            )
        observed = np.array([np.sum(digits == d) for d in range(1, 10)], dtype=float)
        expected = _BENFORD_EXPECTED * len(digits)
        chi2, p_value = stats.chisquare(observed, f_exp=expected)
        score = float(1.0 - p_value)
        digit_fracs = (observed / observed.sum()).tolist()
        return DetectorResult(
            score=score,
            verdict=self._verdict(score),
            plain_english=(
                f"Benford's Law chi-square p={p_value:.4f} — "
                f"{'deviation detected' if score > 0.95 else 'conforms to Benford'}"
            ),
            details={
                "p_value": float(p_value),
                "chi2_statistic": float(chi2),
                "digit_fractions": digit_fracs,
            },
        )
```

- [ ] **Step 4: Create `pattern/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/pattern/__init__.py
from dqt.algorithms.pattern.benford import BenfordDetector

__all__ = ["BenfordDetector"]
```

- [ ] **Step 5: Create empty test `__init__.py`**

Create an empty file: `packages/dqt/tests/algorithms/pattern/__init__.py`

- [ ] **Step 6: Wire into `dqt/__init__.py`**

Add after the info import:

```python
import dqt.algorithms.pattern       # noqa: F401
```

- [ ] **Step 7: Run tests — verify they pass**

```bash
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/pattern/test_benford.py -v 2>&1 | Select-Object -Last 10
```

- [ ] **Step 8: Commit**

```bash
git add packages/dqt/src/dqt/algorithms/pattern/ packages/dqt/src/dqt/__init__.py packages/dqt/tests/algorithms/pattern/
git commit -m "feat(detectors): add benford_law_fit — Benford's Law first-digit test (new pattern group)"
```

---

## Task 10: Full test suite + website sync

**Files:**
- Modify: `apps/web/src/app/page.tsx` — remove non-existent slugs from DETECTORS array

- [ ] **Step 1: Run the full unit test suite**

```bash
cd c:\anton\dqt
uv run pytest packages/dqt/tests/ -q --ignore=packages/dqt/tests/adapters 2>&1 | Select-Object -Last 10
```
Expected: all tests pass (except the pre-existing `test_mad_stability` flakiness).

- [ ] **Step 2: Verify all 10 new slugs are registered**

```bash
cd c:\anton\dqt
uv run python -c "
import dqt
r = dqt.algorithms._registry.registry  # already populated by dqt import
from dqt.algorithms._registry import registry
new_slugs = ['iqr_fence','grubbs','generalized_esd','wasserstein_1','psi','kl_divergence','js_divergence','chi_square_drift','cramers_v','benford_law_fit']
for s in new_slugs:
    cls = registry.get(s)
    print(f'OK  {s} -> {cls.__name__}')
"
```
Expected: 10 lines starting with `OK`.

- [ ] **Step 3: Update website DETECTORS array**

In `apps/web/src/app/page.tsx`, replace the `DETECTORS` const (lines ~49–66) with only actually-registered slugs:

```tsx
const DETECTORS = [
  // Univariate outliers
  "mad_outlier_fraction", "double_mad_outlier_fraction", "zscore_outlier_fraction",
  "adjusted_boxplot_fraction", "auto_outlier", "isolation_forest_fraction",
  "iqr_fence", "grubbs", "generalized_esd",
  // Drift
  "ks_pvalue", "wasserstein_1", "psi", "kl_divergence", "js_divergence", "chi_square_drift",
  // Time series
  "stl_residual_zscore",
  // Info / pattern
  "cramers_v", "benford_law_fit",
];
```

Also update the stat band count from `"30+"` to `"19"` (accurate count of statistical/ML detectors):

```tsx
{ value: "19", label: "statistical algorithms", color: "var(--accent)" },
```

- [ ] **Step 4: Commit everything**

```bash
git add apps/web/src/app/page.tsx
git commit -m "fix(website): sync DETECTORS array with actually-registered slugs (19 live)"
```

- [ ] **Step 5: Final push**

```bash
git push
```

---

## Self-Review

**Spec coverage:**
- ✅ `iqr_fence` — Task 2
- ✅ `grubbs` — Task 3
- ✅ `generalized_esd` — Task 3
- ✅ `wasserstein_1` — Task 4
- ✅ `psi` — Task 5
- ✅ `kl_divergence` — Task 6
- ✅ `js_divergence` — Task 6
- ✅ `chi_square_drift` — Task 7
- ✅ `cramers_v` — Task 8
- ✅ `benford_law_fit` — Task 9
- ✅ STAT_SCALES — Task 1
- ✅ `__init__.py` registration — each task
- ✅ `dqt/__init__.py` imports for new groups — Tasks 8, 9
- ✅ Website sync — Task 10

**Placeholder scan:** No TBDs, all code is complete and exact.

**Type consistency:**
- All detectors use `DetectorState = Any` (dict in practice) — consistent with existing pattern
- All `score()` methods return `DetectorResult` — consistent
- All slugs in STAT_SCALES match class `slug` attributes exactly
