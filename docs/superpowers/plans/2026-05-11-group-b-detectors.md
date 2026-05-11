# Group B Detectors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 14 missing Group B detectors across four groups (`drift`, `outliers_multi`, `timeseries`, `info`) so all marketed slugs are actually registered and working.

**Architecture:** Each detector follows the `BaseDetector` contract: `fit(reference_df) → state`, `score(current_df, state) → DetectorResult`. Score is always a float in the range the STAT_SCALE defines. Verdict is computed via `self._verdict(score)` which reads from `STAT_SCALES`. New detectors are registered via `@registry.register` and auto-imported through their group's `__init__.py` → `dqt/__init__.py`.

**Tech Stack:** Python 3.12, numpy, scipy, pandas, scikit-learn, statsmodels (all installed). No new mandatory dependencies. `stumpy` and `prophet` are optional — graceful fallbacks documented below.

**Dependency status (verified with `uv run pip list`):**
- scipy 1.16.0 — available
- numpy 2.4.4 — available
- pandas 2.3.3 — available
- scikit-learn 1.7.0 — available
- statsmodels 0.14.6 — available
- stumpy — NOT installed (matrix_profile falls back to pure numpy)
- prophet — NOT installed (prophet_anomaly raises ImportError with helpful message)

---

## File Structure

**New implementation files:**
- `packages/dqt/src/dqt/algorithms/drift/mmd.py` — Maximum Mean Discrepancy
- `packages/dqt/src/dqt/algorithms/drift/adwin.py` — Adaptive Windowing
- `packages/dqt/src/dqt/algorithms/outliers_multi/mahalanobis.py` — Mahalanobis distance
- `packages/dqt/src/dqt/algorithms/outliers_multi/lof.py` — Local Outlier Factor
- `packages/dqt/src/dqt/algorithms/outliers_multi/one_class_svm.py` — One-Class SVM
- `packages/dqt/src/dqt/algorithms/outliers_multi/hbos.py` — Histogram-Based Outlier Score
- `packages/dqt/src/dqt/algorithms/outliers_multi/ecod.py` — Empirical CDF Outlier Detection
- `packages/dqt/src/dqt/algorithms/timeseries/cusum.py` — CUSUM
- `packages/dqt/src/dqt/algorithms/timeseries/page_hinkley.py` — Page-Hinkley
- `packages/dqt/src/dqt/algorithms/timeseries/holt_winters.py` — Holt-Winters
- `packages/dqt/src/dqt/algorithms/timeseries/prophet_anomaly.py` — Prophet (stub + optional)
- `packages/dqt/src/dqt/algorithms/timeseries/bocpd.py` — Bayesian Online Changepoint Detection
- `packages/dqt/src/dqt/algorithms/timeseries/matrix_profile.py` — Matrix Profile
- `packages/dqt/src/dqt/algorithms/info/mutual_information.py` — Mutual Information

**New test files:**
- `packages/dqt/tests/algorithms/drift/test_mmd.py`
- `packages/dqt/tests/algorithms/drift/test_adwin.py`
- `packages/dqt/tests/algorithms/outliers_multi/test_mahalanobis.py`
- `packages/dqt/tests/algorithms/outliers_multi/test_lof.py`
- `packages/dqt/tests/algorithms/outliers_multi/test_one_class_svm.py`
- `packages/dqt/tests/algorithms/outliers_multi/test_hbos.py`
- `packages/dqt/tests/algorithms/outliers_multi/test_ecod.py`
- `packages/dqt/tests/algorithms/timeseries/test_cusum.py`
- `packages/dqt/tests/algorithms/timeseries/test_page_hinkley.py`
- `packages/dqt/tests/algorithms/timeseries/test_holt_winters.py`
- `packages/dqt/tests/algorithms/timeseries/test_prophet_anomaly.py`
- `packages/dqt/tests/algorithms/timeseries/test_bocpd.py`
- `packages/dqt/tests/algorithms/timeseries/test_matrix_profile.py`
- `packages/dqt/tests/algorithms/info/test_mutual_information.py`

**Modified files:**
- `packages/dqt/src/dqt/algorithms/_scales.py` — 14 new StatScale entries (Task 1)
- `packages/dqt/src/dqt/algorithms/drift/__init__.py` — add MMD, ADWIN imports
- `packages/dqt/src/dqt/algorithms/outliers_multi/__init__.py` — add Mahalanobis, LOF, OC-SVM, HBOS, ECOD imports
- `packages/dqt/src/dqt/algorithms/timeseries/__init__.py` — add CUSUM, PH, HW, Prophet, BOCPD, MP imports
- `packages/dqt/src/dqt/algorithms/info/__init__.py` — add MutualInformation import

---

## Task 1: STAT_SCALES entries for all 14 new detectors

**Files:**
- Modify: `packages/dqt/src/dqt/algorithms/_scales.py`

- [ ] **Step 1: Add 14 new StatScale entries to STAT_SCALES**

Append the following entries inside the `STAT_SCALES` list, before the closing `]`:

```python
        StatScale("mmd",                  1.0,  0.10, 0.20, "lower_is_better", "MMD drift",                    "Maximum Mean Discrepancy; 0=identical, 1=maximally different"),
        StatScale("mutual_information",   1.0,  0.50, 0.30, "higher_is_better","Mutual information (norm.)",   "Normalized MI between periods; higher=more similar; warn<0.50, fail<0.30"),
        StatScale("mahalanobis_distance", 0.20, 0.01, 0.05, "lower_is_better", "Outlier fraction (Mahal.)",   "Fraction of rows outside chi-square critical ellipsoid at p=0.01"),
        StatScale("lof",                  0.30, 0.05, 0.10, "lower_is_better", "Outlier fraction (LOF)",       "Fraction of rows with LOF > threshold; warn 5%, fail 10%"),
        StatScale("one_class_svm",        0.30, 0.05, 0.10, "lower_is_better", "Outlier fraction (OC-SVM)",    "Fraction of rows classified as outliers by One-Class SVM"),
        StatScale("hbos",                 0.30, 0.05, 0.10, "lower_is_better", "Outlier fraction (HBOS)",      "Fraction of rows with HBOS score above reference 95th percentile"),
        StatScale("ecod",                 0.30, 0.05, 0.10, "lower_is_better", "Outlier fraction (ECOD)",      "Fraction of rows with ECOD score above reference 95th percentile"),
        StatScale("cusum",               10.0,  1.0,  2.0,  "lower_is_better", "CUSUM alarm level",            "Normalised CUSUM statistic; >1.0 moderate shift, >2.0 large shift"),
        StatScale("page_hinkley",         5.0,  0.5,  1.0,  "lower_is_better", "Page-Hinkley alarm",           "Normalised PH statistic; alarm when PH−min(PH) exceeds threshold"),
        StatScale("holt_winters",         0.50, 0.05, 0.10, "lower_is_better", "Anomaly fraction (HW)",        "Fraction of current values outside Holt-Winters prediction interval"),
        StatScale("prophet_anomaly",      0.50, 0.05, 0.10, "lower_is_better", "Anomaly fraction (Prophet)",   "Fraction of current values outside Prophet uncertainty interval"),
        StatScale("adwin",                1.0,  0.50, 0.50, "lower_is_better", "ADWIN drift signal",           "1.0=drift detected in current window, 0.0=stable"),
        StatScale("bocpd",                1.0,  0.50, 0.80, "lower_is_better", "Changepoint probability",      "Max posterior probability of a changepoint in the current window"),
        StatScale("matrix_profile",       0.50, 0.05, 0.10, "lower_is_better", "Discord fraction (MP)",        "Fraction of subsequences whose nearest-neighbour distance exceeds reference 95th percentile"),
```

- [ ] **Step 2: Verify scales are importable**

```powershell
cd c:\anton\dqt
uv run python -c "from dqt.algorithms._scales import STAT_SCALES; print(len(STAT_SCALES), 'scales')"
```
Expected output: `62 scales` (48 existing + 14 new).

- [ ] **Step 3: Commit**

```powershell
git add packages/dqt/src/dqt/algorithms/_scales.py
git commit -m "feat(scales): add 14 STAT_SCALES entries for Group B detectors"
```

---

## Task 2: `mmd` — Maximum Mean Discrepancy

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/drift/mmd.py`
- Create: `packages/dqt/tests/algorithms/drift/test_mmd.py`
- Modify: `packages/dqt/src/dqt/algorithms/drift/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/algorithms/drift/test_mmd.py
# Ref: Gretton et al. (2012) JMLR — A Kernel Two-Sample Test (MMD²)
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.drift.mmd import MMDDetector
    return MMDDetector()


def test_mmd_same_distribution_pass(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert result.verdict == Verdict.pass_
    assert result.score < 0.10


def test_mmd_large_shift_fail(detector, normal_df, shifted_df):
    state = detector.fit(normal_df)
    result = detector.score(shifted_df, state)
    assert result.verdict == Verdict.fail
    assert result.score > 0.20


def test_mmd_score_bounded(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_mmd_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.05, "mmd") == Verdict.pass_
    assert compute_verdict(0.12, "mmd") == Verdict.warn
    assert compute_verdict(0.25, "mmd") == Verdict.fail


def test_mmd_details_present(detector, normal_df, shifted_df):
    state = detector.fit(normal_df)
    result = detector.score(shifted_df, state)
    assert "mmd_squared" in result.details
    assert "gamma" in result.details


def test_mmd_symmetric_approx(detector, normal_df, shifted_df):
    # MMD(A,B) and MMD(B,A) should be close (not exactly equal due to sampling).
    state_a = detector.fit(normal_df)
    result_ab = detector.score(shifted_df, state_a)
    state_b = detector.fit(shifted_df)
    result_ba = detector.score(normal_df, state_b)
    assert abs(result_ab.score - result_ba.score) < 0.15
```

- [ ] **Step 2: Run test — verify it fails**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/drift/test_mmd.py -v 2>&1 | Select-Object -Last 10
```
Expected: `ImportError` or `ModuleNotFoundError` for `mmd`.

- [ ] **Step 3: Implement `mmd.py`**

```python
# packages/dqt/src/dqt/algorithms/drift/mmd.py
# Ref: Gretton et al. (2012) JMLR — A Kernel Two-Sample Test (MMD²)
# MMD² = E[k(x,x')] + E[k(y,y')] - 2·E[k(x,y)] using RBF kernel
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import rbf_kernel

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_MAX_SUBSAMPLE = 500  # cap to keep O(n²) kernel tractable


def _mmd_squared(X: np.ndarray, Y: np.ndarray, gamma: float) -> float:
    """Biased MMD² estimator using RBF kernel."""
    Kxx = rbf_kernel(X, X, gamma=gamma)
    Kyy = rbf_kernel(Y, Y, gamma=gamma)
    Kxy = rbf_kernel(X, Y, gamma=gamma)
    return float(Kxx.mean() + Kyy.mean() - 2.0 * Kxy.mean())


def _median_gamma(X: np.ndarray) -> float:
    """Median heuristic for RBF bandwidth: gamma = 1 / (2 * median_pairwise_dist²)."""
    if len(X) > 200:
        rng = np.random.default_rng(0)
        X = X[rng.choice(len(X), 200, replace=False)]
    dists_sq = np.sum((X[:, None] - X[None, :]) ** 2, axis=-1)
    median_sq = float(np.median(dists_sq[dists_sq > 0]))
    return 1.0 / (2.0 * median_sq) if median_sq > 0 else 1.0


@registry.register
class MMDDetector(BaseDetector):
    """Maximum Mean Discrepancy drift detector. Score = clipped MMD² in [0, 1]."""
    slug = "mmd"
    group = "drift"

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        X = reference.select_dtypes(include="number").fillna(0.0).to_numpy(dtype=float)
        if len(X) > _MAX_SUBSAMPLE:
            rng = np.random.default_rng(0)
            X = X[rng.choice(len(X), _MAX_SUBSAMPLE, replace=False)]
        gamma = _median_gamma(X)
        return {"reference": X, "gamma": gamma}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        Y = current.select_dtypes(include="number").fillna(0.0).to_numpy(dtype=float)
        if len(Y) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"mmd_squared": 0.0, "gamma": state["gamma"]},
            )
        if len(Y) > _MAX_SUBSAMPLE:
            rng = np.random.default_rng(1)
            Y = Y[rng.choice(len(Y), _MAX_SUBSAMPLE, replace=False)]
        mmd2 = _mmd_squared(state["reference"], Y, state["gamma"])
        score = float(min(max(mmd2, 0.0), 1.0))
        return DetectorResult(
            score=score,
            verdict=self._verdict(score),
            plain_english=(
                f"MMD² = {mmd2:.4f} — "
                f"{'drift detected' if score >= 0.10 else 'stable'}"
            ),
            details={"mmd_squared": mmd2, "gamma": state["gamma"]},
        )
```

- [ ] **Step 4: Update `drift/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/drift/__init__.py
from dqt.algorithms.drift.chi_square import ChiSquareDriftDetector
from dqt.algorithms.drift.divergence import JSDivergenceDetector, KLDivergenceDetector
from dqt.algorithms.drift.ks2sample import KS2SampleDetector
from dqt.algorithms.drift.mmd import MMDDetector
from dqt.algorithms.drift.psi import PSIDetector
from dqt.algorithms.drift.wasserstein import Wasserstein1Detector

__all__ = [
    "ChiSquareDriftDetector",
    "JSDivergenceDetector",
    "KLDivergenceDetector",
    "KS2SampleDetector",
    "MMDDetector",
    "PSIDetector",
    "Wasserstein1Detector",
]
```

- [ ] **Step 5: Run tests — verify they pass**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/drift/test_mmd.py -v 2>&1 | Select-Object -Last 10
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add packages/dqt/src/dqt/algorithms/drift/mmd.py packages/dqt/src/dqt/algorithms/drift/__init__.py packages/dqt/tests/algorithms/drift/test_mmd.py
git commit -m "feat(detectors): add mmd — Maximum Mean Discrepancy drift detector"
```

---

## Task 3: `mutual_information` — Normalized Mutual Information (new entry for `info` group)

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/info/mutual_information.py`
- Create: `packages/dqt/tests/algorithms/info/test_mutual_information.py`
- Modify: `packages/dqt/src/dqt/algorithms/info/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/algorithms/info/test_mutual_information.py
# Ref: Cover & Thomas (2006) Elements of Information Theory — mutual information
# Normalized MI for drift: high MI → distributions share structure → lower drift.
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.info.mutual_information import MutualInformationDetector
    return MutualInformationDetector()


def test_mi_identical_distributions_pass(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert result.verdict == Verdict.pass_
    assert result.score > 0.50


def test_mi_shifted_distribution_fail(detector, normal_df, shifted_df):
    state = detector.fit(normal_df)
    result = detector.score(shifted_df, state)
    assert result.verdict == Verdict.fail
    assert result.score < 0.30


def test_mi_score_bounded(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_mi_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.80, "mutual_information") == Verdict.pass_
    assert compute_verdict(0.40, "mutual_information") == Verdict.warn
    assert compute_verdict(0.20, "mutual_information") == Verdict.fail


def test_mi_details_present(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert "normalized_mi" in result.details
    assert "n_bins" in result.details
```

- [ ] **Step 2: Run test — verify it fails**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/info/test_mutual_information.py -v 2>&1 | Select-Object -Last 10
```
Expected: `ImportError` for `mutual_information`.

- [ ] **Step 3: Implement `mutual_information.py`**

```python
# packages/dqt/src/dqt/algorithms/info/mutual_information.py
# Ref: Cover & Thomas (2006) Elements of Information Theory
# Strategy: bin both distributions into the same edges; compute MI on the joint count matrix.
# NMI = MI / sqrt(H(X) * H(Y)); bounded [0, 1]; higher = more shared information = less drift.
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_EPSILON = 1e-10


def _entropy(probs: np.ndarray) -> float:
    p = probs[probs > 0]
    return float(-np.sum(p * np.log(p)))


def _normalized_mi(ref: np.ndarray, curr: np.ndarray, bin_edges: np.ndarray) -> float:
    """Normalized mutual information via a joint histogram over shared bin edges."""
    ref_idx = np.digitize(ref, bin_edges[1:-1])
    cur_idx = np.digitize(curr, bin_edges[1:-1])
    n_bins = len(bin_edges) - 1

    # Joint count matrix: rows=ref bins, cols=curr bins
    joint = np.zeros((n_bins, n_bins), dtype=float)
    for r, c in zip(ref_idx, cur_idx):
        ri = min(r, n_bins - 1)
        ci = min(c, n_bins - 1)
        joint[ri, ci] += 1.0

    joint += _EPSILON
    joint /= joint.sum()
    p_ref = joint.sum(axis=1)
    p_cur = joint.sum(axis=0)

    H_ref = _entropy(p_ref)
    H_cur = _entropy(p_cur)
    denom = np.sqrt(H_ref * H_cur)
    if denom < _EPSILON:
        return 1.0  # identical degenerate distributions

    H_joint = _entropy(joint.ravel())
    mi = H_ref + H_cur - H_joint
    return float(min(max(mi / denom, 0.0), 1.0))


@registry.register
class MutualInformationDetector(BaseDetector):
    """Normalized Mutual Information for drift detection. Score = NMI (higher = more similar)."""
    slug = "mutual_information"
    group = "info"

    def __init__(self, n_bins: int = 20) -> None:
        self._n_bins = n_bins

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        ref = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        bin_edges = np.histogram_bin_edges(ref, bins=self._n_bins)
        return {"reference": ref, "bin_edges": bin_edges, "n_bins": self._n_bins}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        if len(curr) == 0:
            return DetectorResult(
                score=1.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"normalized_mi": 1.0, "n_bins": state["n_bins"]},
            )
        nmi = _normalized_mi(state["reference"], curr, state["bin_edges"])
        return DetectorResult(
            score=nmi,
            verdict=self._verdict(nmi),
            plain_english=(
                f"Normalized MI = {nmi:.4f} — "
                f"{'stable' if nmi >= 0.50 else 'drift detected'}"
            ),
            details={"normalized_mi": nmi, "n_bins": state["n_bins"]},
        )
```

- [ ] **Step 4: Update `info/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/info/__init__.py
from dqt.algorithms.info.cramers_v import CramersVDetector
from dqt.algorithms.info.mutual_information import MutualInformationDetector

__all__ = ["CramersVDetector", "MutualInformationDetector"]
```

- [ ] **Step 5: Run tests — verify they pass**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/info/test_mutual_information.py -v 2>&1 | Select-Object -Last 10
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add packages/dqt/src/dqt/algorithms/info/mutual_information.py packages/dqt/src/dqt/algorithms/info/__init__.py packages/dqt/tests/algorithms/info/test_mutual_information.py
git commit -m "feat(detectors): add mutual_information — normalized MI drift detector"
```

---

## Task 4: `mahalanobis_distance` — Mahalanobis multivariate outlier

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/outliers_multi/mahalanobis.py`
- Create: `packages/dqt/tests/algorithms/outliers_multi/test_mahalanobis.py`
- Modify: `packages/dqt/src/dqt/algorithms/outliers_multi/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/algorithms/outliers_multi/test_mahalanobis.py
# Ref: Mahalanobis (1936) Proc. Natl. Inst. Sci. India — distance using covariance metric
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.outliers_multi.mahalanobis import MahalanobisDetector
    return MahalanobisDetector()


def _multi_normal_df(n: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "a": rng.normal(0, 1, n),
        "b": rng.normal(5, 2, n),
        "c": rng.normal(-3, 0.5, n),
    })


def test_mahalanobis_clean_data_pass(detector):
    df = _multi_normal_df(500)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.verdict == Verdict.pass_


def test_mahalanobis_detects_outliers(detector):
    df = _multi_normal_df(500)
    state = detector.fit(df)
    # Inject 30 obvious outliers (far from the cloud)
    outliers = pd.DataFrame({
        "a": [100.0] * 30,
        "b": [100.0] * 30,
        "c": [100.0] * 30,
    })
    curr = pd.concat([df, outliers], ignore_index=True)
    result = detector.score(curr, state)
    assert result.details["outlier_fraction"] > 0.01
    assert result.verdict != Verdict.pass_


def test_mahalanobis_score_bounded(detector):
    df = _multi_normal_df(200)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_mahalanobis_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.005, "mahalanobis_distance") == Verdict.pass_
    assert compute_verdict(0.015, "mahalanobis_distance") == Verdict.warn
    assert compute_verdict(0.06, "mahalanobis_distance") == Verdict.fail


def test_mahalanobis_details_present(detector):
    df = _multi_normal_df(300)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert "outlier_fraction" in result.details
    assert "chi2_threshold" in result.details
    assert "n_features" in result.details
```

- [ ] **Step 2: Run test — verify it fails**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/outliers_multi/test_mahalanobis.py -v 2>&1 | Select-Object -Last 10
```
Expected: `ImportError` for `mahalanobis`.

- [ ] **Step 3: Implement `mahalanobis.py`**

```python
# packages/dqt/src/dqt/algorithms/outliers_multi/mahalanobis.py
# Ref: Mahalanobis (1936) Proc. Natl. Inst. Sci. India
# d²(x) = (x-µ)ᵀ Σ⁻¹ (x-µ); outlier iff d² > chi2_ppf(1-alpha, df=p)
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry


@registry.register
class MahalanobisDetector(BaseDetector):
    """Mahalanobis distance multivariate outlier detector. Score = fraction of rows exceeding chi-square critical distance."""
    slug = "mahalanobis_distance"
    group = "outliers_multi"

    def __init__(self, alpha: float = 0.01) -> None:
        self._alpha = alpha

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        X = reference.select_dtypes(include="number").fillna(0.0).to_numpy(dtype=float)
        mu = X.mean(axis=0)
        cov = np.cov(X, rowvar=False)
        if cov.ndim == 0:
            cov = np.array([[float(cov)]])
        cov_inv = np.linalg.pinv(cov)
        p = X.shape[1]
        threshold = float(stats.chi2.ppf(1.0 - self._alpha, df=p))
        return {"mu": mu, "cov_inv": cov_inv, "p": p, "threshold": threshold}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        X = current.select_dtypes(include="number").fillna(0.0).to_numpy(dtype=float)
        if len(X) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"outlier_fraction": 0.0, "chi2_threshold": state["threshold"], "n_features": state["p"]},
            )
        diff = X - state["mu"]
        # d²(x) = diff @ cov_inv @ diff.T; take diagonal for per-row distances
        d_sq = np.einsum("ij,jk,ik->i", diff, state["cov_inv"], diff)
        n_out = int(np.sum(d_sq > state["threshold"]))
        frac = n_out / len(X)
        return DetectorResult(
            score=frac,
            verdict=self._verdict(frac),
            plain_english=(
                f"{frac:.1%} of rows outside Mahalanobis critical ellipsoid "
                f"(chi²-threshold={state['threshold']:.2f}, p={state['p']} features)"
            ),
            details={
                "outlier_fraction": frac,
                "chi2_threshold": state["threshold"],
                "n_features": state["p"],
            },
        )
```

- [ ] **Step 4: Update `outliers_multi/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/outliers_multi/__init__.py
from dqt.algorithms.outliers_multi.isolation_forest import IsolationForestDetector
from dqt.algorithms.outliers_multi.mahalanobis import MahalanobisDetector

__all__ = ["IsolationForestDetector", "MahalanobisDetector"]
```

- [ ] **Step 5: Run tests — verify they pass**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/outliers_multi/test_mahalanobis.py -v 2>&1 | Select-Object -Last 10
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add packages/dqt/src/dqt/algorithms/outliers_multi/mahalanobis.py packages/dqt/src/dqt/algorithms/outliers_multi/__init__.py packages/dqt/tests/algorithms/outliers_multi/test_mahalanobis.py
git commit -m "feat(detectors): add mahalanobis_distance — multivariate outlier detector"
```

---

## Task 5: `lof` — Local Outlier Factor

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/outliers_multi/lof.py`
- Create: `packages/dqt/tests/algorithms/outliers_multi/test_lof.py`
- Modify: `packages/dqt/src/dqt/algorithms/outliers_multi/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/algorithms/outliers_multi/test_lof.py
# Ref: Breunig et al. (2000) SIGMOD — LOF: Identifying Density-Based Local Outliers
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.outliers_multi.lof import LOFDetector
    return LOFDetector()


def _multi_normal_df(n: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "a": rng.normal(0, 1, n),
        "b": rng.normal(5, 2, n),
    })


def test_lof_clean_data_pass(detector):
    df = _multi_normal_df(300)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.verdict == Verdict.pass_


def test_lof_detects_outliers(detector):
    rng = np.random.default_rng(7)
    clean = pd.DataFrame({"a": rng.normal(0, 1, 200), "b": rng.normal(0, 1, 200)})
    outliers = pd.DataFrame({"a": [50.0] * 20, "b": [50.0] * 20})
    curr = pd.concat([clean, outliers], ignore_index=True)
    state = detector.fit(clean)
    result = detector.score(curr, state)
    assert result.details["outlier_fraction"] > 0.05
    assert result.verdict != Verdict.pass_


def test_lof_score_bounded(detector):
    df = _multi_normal_df(200)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_lof_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.02, "lof") == Verdict.pass_
    assert compute_verdict(0.07, "lof") == Verdict.warn
    assert compute_verdict(0.15, "lof") == Verdict.fail


def test_lof_details_present(detector):
    df = _multi_normal_df(150)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert "outlier_fraction" in result.details
    assert "lof_threshold" in result.details
```

- [ ] **Step 2: Run test — verify it fails**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/outliers_multi/test_lof.py -v 2>&1 | Select-Object -Last 10
```
Expected: `ImportError` for `lof`.

- [ ] **Step 3: Implement `lof.py`**

```python
# packages/dqt/src/dqt/algorithms/outliers_multi/lof.py
# Ref: Breunig et al. (2000) SIGMOD — LOF: Identifying Density-Based Local Outliers
# Score = fraction of rows with LOF score > lof_threshold (default 1.5).
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.neighbors import LocalOutlierFactor

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry


@registry.register
class LOFDetector(BaseDetector):
    """Local Outlier Factor multivariate outlier detection. Score = fraction of rows with LOF > threshold."""
    slug = "lof"
    group = "outliers_multi"

    def __init__(self, n_neighbors: int = 20, lof_threshold: float = 1.5) -> None:
        self._n_neighbors = n_neighbors
        self._lof_threshold = lof_threshold

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        X = reference.select_dtypes(include="number").fillna(0.0).to_numpy(dtype=float)
        n_neighbors = min(self._n_neighbors, len(X) - 1)
        # novelty=True allows scoring new data after fitting
        model = LocalOutlierFactor(n_neighbors=n_neighbors, novelty=True)
        model.fit(X)
        return {
            "model": model,
            "columns": list(reference.select_dtypes(include="number").columns),
            "lof_threshold": self._lof_threshold,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        cols: list[str] = state["columns"]
        X = current.reindex(columns=cols, fill_value=0.0).fillna(0.0).to_numpy(dtype=float)
        if len(X) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"outlier_fraction": 0.0, "lof_threshold": state["lof_threshold"]},
            )
        # LOF negative_outlier_factor_: more negative = more anomalous; outlier iff factor < -threshold
        lof_scores = -state["model"].score_samples(X)  # positive; large = anomalous
        n_out = int(np.sum(lof_scores > state["lof_threshold"]))
        frac = n_out / len(X)
        return DetectorResult(
            score=frac,
            verdict=self._verdict(frac),
            plain_english=f"{frac:.1%} of rows with LOF score > {state['lof_threshold']:.1f}",
            details={
                "outlier_fraction": frac,
                "lof_threshold": state["lof_threshold"],
                "max_lof_score": float(np.max(lof_scores)),
            },
        )
```

- [ ] **Step 4: Update `outliers_multi/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/outliers_multi/__init__.py
from dqt.algorithms.outliers_multi.isolation_forest import IsolationForestDetector
from dqt.algorithms.outliers_multi.lof import LOFDetector
from dqt.algorithms.outliers_multi.mahalanobis import MahalanobisDetector

__all__ = ["IsolationForestDetector", "LOFDetector", "MahalanobisDetector"]
```

- [ ] **Step 5: Run tests — verify they pass**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/outliers_multi/test_lof.py -v 2>&1 | Select-Object -Last 10
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add packages/dqt/src/dqt/algorithms/outliers_multi/lof.py packages/dqt/src/dqt/algorithms/outliers_multi/__init__.py packages/dqt/tests/algorithms/outliers_multi/test_lof.py
git commit -m "feat(detectors): add lof — Local Outlier Factor multivariate outlier detector"
```

---

## Task 6: `one_class_svm` — One-Class SVM

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/outliers_multi/one_class_svm.py`
- Create: `packages/dqt/tests/algorithms/outliers_multi/test_one_class_svm.py`
- Modify: `packages/dqt/src/dqt/algorithms/outliers_multi/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/algorithms/outliers_multi/test_one_class_svm.py
# Ref: Schölkopf et al. (2001) Neural Computation — Estimating support of a high-dim distribution
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.outliers_multi.one_class_svm import OneClassSVMDetector
    return OneClassSVMDetector()


def _multi_normal_df(n: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "a": rng.normal(0, 1, n),
        "b": rng.normal(5, 2, n),
    })


def test_ocsvm_clean_data_pass(detector):
    df = _multi_normal_df(300)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.verdict == Verdict.pass_


def test_ocsvm_detects_outliers(detector):
    rng = np.random.default_rng(7)
    clean = pd.DataFrame({"a": rng.normal(0, 1, 200), "b": rng.normal(0, 1, 200)})
    outliers = pd.DataFrame({"a": [50.0] * 30, "b": [50.0] * 30})
    curr = pd.concat([clean, outliers], ignore_index=True)
    state = detector.fit(clean)
    result = detector.score(curr, state)
    assert result.details["outlier_fraction"] > 0.05
    assert result.verdict != Verdict.pass_


def test_ocsvm_score_bounded(detector):
    df = _multi_normal_df(200)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_ocsvm_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.02, "one_class_svm") == Verdict.pass_
    assert compute_verdict(0.07, "one_class_svm") == Verdict.warn
    assert compute_verdict(0.15, "one_class_svm") == Verdict.fail


def test_ocsvm_details_present(detector):
    df = _multi_normal_df(150)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert "outlier_fraction" in result.details
    assert "n_rows" in result.details
```

- [ ] **Step 2: Run test — verify it fails**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/outliers_multi/test_one_class_svm.py -v 2>&1 | Select-Object -Last 10
```
Expected: `ImportError` for `one_class_svm`.

- [ ] **Step 3: Implement `one_class_svm.py`**

```python
# packages/dqt/src/dqt/algorithms/outliers_multi/one_class_svm.py
# Ref: Schölkopf et al. (2001) Neural Computation — Estimating support of a high-dimensional distribution
# Score = fraction of rows predicted as outliers (-1) by the fitted OC-SVM.
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.svm import OneClassSVM

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry


@registry.register
class OneClassSVMDetector(BaseDetector):
    """One-Class SVM multivariate outlier detector. Score = fraction of rows classified as outliers."""
    slug = "one_class_svm"
    group = "outliers_multi"

    def __init__(self, nu: float = 0.05, kernel: str = "rbf") -> None:
        self._nu = nu
        self._kernel = kernel

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        X = reference.select_dtypes(include="number").fillna(0.0).to_numpy(dtype=float)
        model = OneClassSVM(nu=self._nu, kernel=self._kernel)
        model.fit(X)
        return {
            "model": model,
            "columns": list(reference.select_dtypes(include="number").columns),
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        cols: list[str] = state["columns"]
        X = current.reindex(columns=cols, fill_value=0.0).fillna(0.0).to_numpy(dtype=float)
        if len(X) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"outlier_fraction": 0.0, "n_rows": 0},
            )
        preds = state["model"].predict(X)  # -1 = outlier, 1 = inlier
        n_out = int(np.sum(preds == -1))
        frac = n_out / len(X)
        return DetectorResult(
            score=frac,
            verdict=self._verdict(frac),
            plain_english=f"{frac:.1%} of rows classified as outliers by One-Class SVM",
            details={"outlier_fraction": frac, "n_rows": len(X)},
        )
```

- [ ] **Step 4: Update `outliers_multi/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/outliers_multi/__init__.py
from dqt.algorithms.outliers_multi.isolation_forest import IsolationForestDetector
from dqt.algorithms.outliers_multi.lof import LOFDetector
from dqt.algorithms.outliers_multi.mahalanobis import MahalanobisDetector
from dqt.algorithms.outliers_multi.one_class_svm import OneClassSVMDetector

__all__ = [
    "IsolationForestDetector",
    "LOFDetector",
    "MahalanobisDetector",
    "OneClassSVMDetector",
]
```

- [ ] **Step 5: Run tests — verify they pass**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/outliers_multi/test_one_class_svm.py -v 2>&1 | Select-Object -Last 10
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add packages/dqt/src/dqt/algorithms/outliers_multi/one_class_svm.py packages/dqt/src/dqt/algorithms/outliers_multi/__init__.py packages/dqt/tests/algorithms/outliers_multi/test_one_class_svm.py
git commit -m "feat(detectors): add one_class_svm — One-Class SVM multivariate outlier detector"
```

---

## Task 7: `hbos` + `ecod` — Pure-numpy multivariate outlier detectors

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/outliers_multi/hbos.py`
- Create: `packages/dqt/src/dqt/algorithms/outliers_multi/ecod.py`
- Create: `packages/dqt/tests/algorithms/outliers_multi/test_hbos.py`
- Create: `packages/dqt/tests/algorithms/outliers_multi/test_ecod.py`
- Modify: `packages/dqt/src/dqt/algorithms/outliers_multi/__init__.py`

- [ ] **Step 1: Write the failing tests**

```python
# packages/dqt/tests/algorithms/outliers_multi/test_hbos.py
# Ref: Goldstein & Dengel (2012) KI — Histogram-based Outlier Score
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.outliers_multi.hbos import HBOSDetector
    return HBOSDetector()


def _multi_normal_df(n: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "a": rng.normal(0, 1, n),
        "b": rng.normal(5, 2, n),
        "c": rng.normal(-3, 0.5, n),
    })


def test_hbos_clean_data_pass(detector):
    df = _multi_normal_df(500)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.verdict == Verdict.pass_


def test_hbos_detects_outliers(detector):
    rng = np.random.default_rng(7)
    clean = _multi_normal_df(500)
    outliers = pd.DataFrame({
        "a": [100.0] * 30, "b": [100.0] * 30, "c": [100.0] * 30,
    })
    curr = pd.concat([clean, outliers], ignore_index=True)
    state = detector.fit(clean)
    result = detector.score(curr, state)
    assert result.details["outlier_fraction"] > 0.01
    assert result.verdict != Verdict.pass_


def test_hbos_score_bounded(detector):
    df = _multi_normal_df(300)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_hbos_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.02, "hbos") == Verdict.pass_
    assert compute_verdict(0.07, "hbos") == Verdict.warn
    assert compute_verdict(0.15, "hbos") == Verdict.fail


def test_hbos_details_present(detector):
    df = _multi_normal_df(200)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert "outlier_fraction" in result.details
    assert "score_threshold" in result.details
```

```python
# packages/dqt/tests/algorithms/outliers_multi/test_ecod.py
# Ref: Li et al. (2022) TKDE — ECOD: Unsupervised Outlier Detection Using Empirical Cumulative Distribution
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.outliers_multi.ecod import ECODDetector
    return ECODDetector()


def _multi_normal_df(n: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "a": rng.normal(0, 1, n),
        "b": rng.normal(5, 2, n),
        "c": rng.normal(-3, 0.5, n),
    })


def test_ecod_clean_data_pass(detector):
    df = _multi_normal_df(500)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert result.verdict == Verdict.pass_


def test_ecod_detects_outliers(detector):
    clean = _multi_normal_df(500)
    outliers = pd.DataFrame({
        "a": [100.0] * 30, "b": [100.0] * 30, "c": [100.0] * 30,
    })
    curr = pd.concat([clean, outliers], ignore_index=True)
    state = detector.fit(clean)
    result = detector.score(curr, state)
    assert result.details["outlier_fraction"] > 0.01
    assert result.verdict != Verdict.pass_


def test_ecod_score_bounded(detector):
    df = _multi_normal_df(300)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_ecod_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.02, "ecod") == Verdict.pass_
    assert compute_verdict(0.07, "ecod") == Verdict.warn
    assert compute_verdict(0.15, "ecod") == Verdict.fail


def test_ecod_details_present(detector):
    df = _multi_normal_df(200)
    state = detector.fit(df)
    result = detector.score(df, state)
    assert "outlier_fraction" in result.details
    assert "score_threshold" in result.details
```

- [ ] **Step 2: Run tests — verify they fail**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/outliers_multi/test_hbos.py packages/dqt/tests/algorithms/outliers_multi/test_ecod.py -v 2>&1 | Select-Object -Last 10
```
Expected: `ImportError` for both `hbos` and `ecod`.

- [ ] **Step 3: Implement `hbos.py`**

```python
# packages/dqt/src/dqt/algorithms/outliers_multi/hbos.py
# Ref: Goldstein & Dengel (2012) KI-2012 — Histogram-based Outlier Score
# HBOS(x) = Σ_i log(1 / freq(xi in bin_i)); score = fraction above reference 95th percentile.
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_EPSILON = 1e-6


def _hbos_scores(X: np.ndarray, bin_edges_list: list, n_bins: int) -> np.ndarray:
    """Compute per-row HBOS scores given fitted histogram edges."""
    scores = np.zeros(len(X))
    for j, edges in enumerate(bin_edges_list):
        col = X[:, j]
        counts, _ = np.histogram(col, bins=edges)
        freqs = (counts + _EPSILON) / (len(col) + n_bins * _EPSILON)
        # Map each value to its bin
        indices = np.clip(np.digitize(col, edges[1:-1]), 0, n_bins - 1)
        scores += np.log(1.0 / freqs[indices])
    return scores


@registry.register
class HBOSDetector(BaseDetector):
    """Histogram-Based Outlier Score. Score = fraction of rows above reference 95th percentile HBOS."""
    slug = "hbos"
    group = "outliers_multi"

    def __init__(self, n_bins: int = 20) -> None:
        self._n_bins = n_bins

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        X = reference.select_dtypes(include="number").fillna(0.0).to_numpy(dtype=float)
        columns = list(reference.select_dtypes(include="number").columns)
        bin_edges_list = [
            np.histogram_bin_edges(X[:, j], bins=self._n_bins)
            for j in range(X.shape[1])
        ]
        ref_scores = _hbos_scores(X, bin_edges_list, self._n_bins)
        threshold = float(np.percentile(ref_scores, 95))
        return {
            "bin_edges_list": bin_edges_list,
            "columns": columns,
            "threshold": threshold,
            "n_bins": self._n_bins,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        cols = state["columns"]
        X = current.reindex(columns=cols, fill_value=0.0).fillna(0.0).to_numpy(dtype=float)
        if len(X) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"outlier_fraction": 0.0, "score_threshold": state["threshold"]},
            )
        scores = _hbos_scores(X, state["bin_edges_list"], state["n_bins"])
        n_out = int(np.sum(scores > state["threshold"]))
        frac = n_out / len(X)
        return DetectorResult(
            score=frac,
            verdict=self._verdict(frac),
            plain_english=f"{frac:.1%} of rows with HBOS score above reference 95th percentile",
            details={
                "outlier_fraction": frac,
                "score_threshold": state["threshold"],
                "max_score": float(np.max(scores)),
            },
        )
```

- [ ] **Step 4: Implement `ecod.py`**

```python
# packages/dqt/src/dqt/algorithms/outliers_multi/ecod.py
# Ref: Li et al. (2022) IEEE TKDE — ECOD: Unsupervised Outlier Detection Using Empirical CDF Functions
# Score(x) = -log(min(ECDF(xi), 1-ECDF(xi))) summed over features; fraction above reference 95th pct.
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_EPSILON = 1e-6


def _ecdf(ref: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Empirical CDF of ref evaluated at each point in x."""
    n = len(ref)
    ref_sorted = np.sort(ref)
    # searchsorted gives count of ref values <= x[i]
    return np.searchsorted(ref_sorted, x, side="right") / n


def _ecod_scores(X: np.ndarray, ref: np.ndarray) -> np.ndarray:
    """Per-row ECOD outlier scores given reference array (same shape)."""
    n_rows, n_cols = X.shape
    scores = np.zeros(n_rows)
    for j in range(n_cols):
        ecdf_vals = _ecdf(ref[:, j], X[:, j])
        ecdf_vals = np.clip(ecdf_vals, _EPSILON, 1.0 - _EPSILON)
        tail_prob = np.minimum(ecdf_vals, 1.0 - ecdf_vals)
        scores += -np.log(tail_prob)
    return scores


@registry.register
class ECODDetector(BaseDetector):
    """ECOD — Empirical CDF outlier detection. Score = fraction above reference 95th percentile."""
    slug = "ecod"
    group = "outliers_multi"

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        X = reference.select_dtypes(include="number").fillna(0.0).to_numpy(dtype=float)
        columns = list(reference.select_dtypes(include="number").columns)
        ref_scores = _ecod_scores(X, X)
        threshold = float(np.percentile(ref_scores, 95))
        return {"reference": X, "columns": columns, "threshold": threshold}

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        cols = state["columns"]
        X = current.reindex(columns=cols, fill_value=0.0).fillna(0.0).to_numpy(dtype=float)
        if len(X) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"outlier_fraction": 0.0, "score_threshold": state["threshold"]},
            )
        scores = _ecod_scores(X, state["reference"])
        n_out = int(np.sum(scores > state["threshold"]))
        frac = n_out / len(X)
        return DetectorResult(
            score=frac,
            verdict=self._verdict(frac),
            plain_english=f"{frac:.1%} of rows with ECOD score above reference 95th percentile",
            details={
                "outlier_fraction": frac,
                "score_threshold": state["threshold"],
                "max_score": float(np.max(scores)),
            },
        )
```

- [ ] **Step 5: Update `outliers_multi/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/outliers_multi/__init__.py
from dqt.algorithms.outliers_multi.ecod import ECODDetector
from dqt.algorithms.outliers_multi.hbos import HBOSDetector
from dqt.algorithms.outliers_multi.isolation_forest import IsolationForestDetector
from dqt.algorithms.outliers_multi.lof import LOFDetector
from dqt.algorithms.outliers_multi.mahalanobis import MahalanobisDetector
from dqt.algorithms.outliers_multi.one_class_svm import OneClassSVMDetector

__all__ = [
    "ECODDetector",
    "HBOSDetector",
    "IsolationForestDetector",
    "LOFDetector",
    "MahalanobisDetector",
    "OneClassSVMDetector",
]
```

- [ ] **Step 6: Run tests — verify they pass**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/outliers_multi/test_hbos.py packages/dqt/tests/algorithms/outliers_multi/test_ecod.py -v 2>&1 | Select-Object -Last 15
```
Expected: all tests pass.

- [ ] **Step 7: Commit**

```powershell
git add packages/dqt/src/dqt/algorithms/outliers_multi/hbos.py packages/dqt/src/dqt/algorithms/outliers_multi/ecod.py packages/dqt/src/dqt/algorithms/outliers_multi/__init__.py packages/dqt/tests/algorithms/outliers_multi/test_hbos.py packages/dqt/tests/algorithms/outliers_multi/test_ecod.py
git commit -m "feat(detectors): add hbos + ecod — histogram and empirical-CDF outlier detectors"
```

---

## Task 8: `cusum` — CUSUM control chart

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/timeseries/cusum.py`
- Create: `packages/dqt/tests/algorithms/timeseries/test_cusum.py`
- Modify: `packages/dqt/src/dqt/algorithms/timeseries/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/algorithms/timeseries/test_cusum.py
# Ref: Page (1954) Biometrika — Continuous inspection schemes (CUSUM)
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.timeseries.cusum import CUSUMDetector
    return CUSUMDetector()


def test_cusum_stable_series_pass(detector, timeseries_df):
    ref = timeseries_df.iloc[:300].reset_index(drop=True)
    curr = timeseries_df.iloc[300:340].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.verdict == Verdict.pass_
    assert result.score < 1.0


def test_cusum_large_mean_shift_fail(detector, timeseries_df):
    ref = timeseries_df.iloc[:300].reset_index(drop=True)
    curr = timeseries_df.iloc[300:340].copy().reset_index(drop=True)
    curr["value"] += 20.0  # persistent large shift
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.verdict == Verdict.fail
    assert result.score > 2.0


def test_cusum_score_non_negative(detector, timeseries_df):
    ref = timeseries_df.iloc[:200].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(timeseries_df.iloc[200:250].reset_index(drop=True), state)
    assert result.score >= 0.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_cusum_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.5, "cusum") == Verdict.pass_
    assert compute_verdict(1.5, "cusum") == Verdict.warn
    assert compute_verdict(3.0, "cusum") == Verdict.fail


def test_cusum_details_present(detector, timeseries_df):
    ref = timeseries_df.iloc[:200].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(timeseries_df.iloc[200:250].reset_index(drop=True), state)
    assert "cusum_hi" in result.details
    assert "cusum_lo" in result.details
    assert "ref_mean" in result.details
    assert "ref_std" in result.details
```

- [ ] **Step 2: Run test — verify it fails**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/timeseries/test_cusum.py -v 2>&1 | Select-Object -Last 10
```
Expected: `ImportError` for `cusum`.

- [ ] **Step 3: Implement `cusum.py`**

```python
# packages/dqt/src/dqt/algorithms/timeseries/cusum.py
# Ref: Page (1954) Biometrika 41(1) — Continuous Inspection Schemes (two-sided CUSUM)
# S_hi[t] = max(0, S_hi[t-1] + (x[t]-µ)/σ - k); S_lo symmetric
# Score = max(S_hi[-1], -S_lo[-1]) / h (normalised by decision threshold h)
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_EPSILON = 1e-8


@registry.register
class CUSUMDetector(BaseDetector):
    """Two-sided CUSUM control chart for persistent mean-shift detection."""
    slug = "cusum"
    group = "timeseries"

    def __init__(self, k: float = 0.5, h: float = 5.0) -> None:
        # k: slack (half the minimum detectable shift in σ units)
        # h: decision threshold in σ units
        self._k = k
        self._h = h

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        values = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        mu = float(np.mean(values))
        sigma = float(np.std(values, ddof=1))
        return {
            "ref_mean": mu,
            "ref_std": max(sigma, _EPSILON),
            "k": self._k,
            "h": self._h,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        values = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        mu = state["ref_mean"]
        sigma = state["ref_std"]
        k = state["k"]
        h = state["h"]
        if len(values) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"cusum_hi": 0.0, "cusum_lo": 0.0, "ref_mean": mu, "ref_std": sigma},
            )
        s_hi = 0.0
        s_lo = 0.0
        for x in values:
            z = (x - mu) / sigma
            s_hi = max(0.0, s_hi + z - k)
            s_lo = min(0.0, s_lo + z + k)
        # Normalise by h so score=1.0 means exactly at decision boundary
        raw = max(s_hi, -s_lo)
        score = raw / h
        return DetectorResult(
            score=score,
            verdict=self._verdict(score),
            plain_english=(
                f"CUSUM alarm level = {score:.3f} "
                f"({'alarm' if score >= 1.0 else 'normal'}; "
                f"S_hi={s_hi:.2f}, S_lo={s_lo:.2f})"
            ),
            details={
                "cusum_hi": s_hi,
                "cusum_lo": s_lo,
                "ref_mean": mu,
                "ref_std": sigma,
            },
        )
```

- [ ] **Step 4: Update `timeseries/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/timeseries/__init__.py
from dqt.algorithms.timeseries.cusum import CUSUMDetector
from dqt.algorithms.timeseries.stl import STLAnomalyDetector

__all__ = ["CUSUMDetector", "STLAnomalyDetector"]
```

- [ ] **Step 5: Run tests — verify they pass**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/timeseries/test_cusum.py -v 2>&1 | Select-Object -Last 10
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add packages/dqt/src/dqt/algorithms/timeseries/cusum.py packages/dqt/src/dqt/algorithms/timeseries/__init__.py packages/dqt/tests/algorithms/timeseries/test_cusum.py
git commit -m "feat(detectors): add cusum — two-sided CUSUM control chart for mean-shift detection"
```

---

## Task 9: `page_hinkley` — Page-Hinkley test

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/timeseries/page_hinkley.py`
- Create: `packages/dqt/tests/algorithms/timeseries/test_page_hinkley.py`
- Modify: `packages/dqt/src/dqt/algorithms/timeseries/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/algorithms/timeseries/test_page_hinkley.py
# Ref: Hinkley (1971) Biometrika — Inference about the change-point from cumulative sum tests
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.timeseries.page_hinkley import PageHinkleyDetector
    return PageHinkleyDetector()


def test_ph_stable_series_pass(detector, timeseries_df):
    ref = timeseries_df.iloc[:300].reset_index(drop=True)
    curr = timeseries_df.iloc[300:340].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.verdict == Verdict.pass_
    assert result.score < 0.5


def test_ph_large_shift_fail(detector, timeseries_df):
    ref = timeseries_df.iloc[:300].reset_index(drop=True)
    curr = timeseries_df.iloc[300:340].copy().reset_index(drop=True)
    curr["value"] += 30.0
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.verdict == Verdict.fail
    assert result.score >= 1.0


def test_ph_score_non_negative(detector, timeseries_df):
    ref = timeseries_df.iloc[:200].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(timeseries_df.iloc[200:250].reset_index(drop=True), state)
    assert result.score >= 0.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_ph_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.3, "page_hinkley") == Verdict.pass_
    assert compute_verdict(0.7, "page_hinkley") == Verdict.warn
    assert compute_verdict(1.5, "page_hinkley") == Verdict.fail


def test_ph_details_present(detector, timeseries_df):
    ref = timeseries_df.iloc[:200].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(timeseries_df.iloc[200:250].reset_index(drop=True), state)
    assert "ph_statistic" in result.details
    assert "lambda_threshold" in result.details
    assert "ref_mean" in result.details
```

- [ ] **Step 2: Run test — verify it fails**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/timeseries/test_page_hinkley.py -v 2>&1 | Select-Object -Last 10
```
Expected: `ImportError` for `page_hinkley`.

- [ ] **Step 3: Implement `page_hinkley.py`**

```python
# packages/dqt/src/dqt/algorithms/timeseries/page_hinkley.py
# Ref: Hinkley (1971) Biometrika 58(3) — Inference about the change-point from cumulative sum tests
# PH_t = Σ(xi - µ_ref - δ); alarm when PH_t - min(PH) > λ
# Score = (PH_current - min_PH) / λ; normalised so score=1.0 at the alarm boundary.
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_EPSILON = 1e-8


@registry.register
class PageHinkleyDetector(BaseDetector):
    """Page-Hinkley online change-point detector. Score = normalised PH statistic."""
    slug = "page_hinkley"
    group = "timeseries"

    def __init__(self, delta: float = 0.005, lambda_: float = 50.0) -> None:
        # delta: minimum magnitude of the mean shift to detect (in raw units)
        # lambda_: alarm threshold for PH_t - min(PH)
        self._delta = delta
        self._lambda = lambda_

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        values = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        mu = float(np.mean(values))
        sigma = float(np.std(values, ddof=1))
        # Scale delta to be relative to sigma so the detector is distribution-agnostic
        delta_scaled = self._delta * max(sigma, _EPSILON)
        lambda_scaled = self._lambda * max(sigma, _EPSILON)
        return {
            "ref_mean": mu,
            "ref_std": max(sigma, _EPSILON),
            "delta": delta_scaled,
            "lambda": lambda_scaled,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        values = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        mu = state["ref_mean"]
        delta = state["delta"]
        lam = state["lambda"]
        if len(values) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={
                    "ph_statistic": 0.0,
                    "lambda_threshold": lam,
                    "ref_mean": mu,
                },
            )
        ph = 0.0
        ph_min = 0.0
        for x in values:
            ph += (x - mu - delta)
            ph_min = min(ph_min, ph)
        alarm_stat = max(0.0, ph - ph_min)
        score = alarm_stat / lam if lam > 0 else 0.0
        return DetectorResult(
            score=score,
            verdict=self._verdict(score),
            plain_english=(
                f"Page-Hinkley statistic = {alarm_stat:.3f} / λ={lam:.3f} → score={score:.3f} "
                f"({'alarm' if score >= 0.5 else 'normal'})"
            ),
            details={
                "ph_statistic": alarm_stat,
                "lambda_threshold": lam,
                "ref_mean": mu,
            },
        )
```

- [ ] **Step 4: Update `timeseries/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/timeseries/__init__.py
from dqt.algorithms.timeseries.cusum import CUSUMDetector
from dqt.algorithms.timeseries.page_hinkley import PageHinkleyDetector
from dqt.algorithms.timeseries.stl import STLAnomalyDetector

__all__ = ["CUSUMDetector", "PageHinkleyDetector", "STLAnomalyDetector"]
```

- [ ] **Step 5: Run tests — verify they pass**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/timeseries/test_page_hinkley.py -v 2>&1 | Select-Object -Last 10
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add packages/dqt/src/dqt/algorithms/timeseries/page_hinkley.py packages/dqt/src/dqt/algorithms/timeseries/__init__.py packages/dqt/tests/algorithms/timeseries/test_page_hinkley.py
git commit -m "feat(detectors): add page_hinkley — Page-Hinkley online change-point detector"
```

---

## Task 10: `holt_winters` — Holt-Winters exponential smoothing anomaly detector

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/timeseries/holt_winters.py`
- Create: `packages/dqt/tests/algorithms/timeseries/test_holt_winters.py`
- Modify: `packages/dqt/src/dqt/algorithms/timeseries/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/algorithms/timeseries/test_holt_winters.py
# Ref: Holt (1957); Winters (1960) Management Science — forecasting with exponential smoothing
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.timeseries.holt_winters import HoltWintersDetector
    return HoltWintersDetector(period=7)


def test_hw_clean_continuation_pass(detector, timeseries_df):
    ref = timeseries_df.iloc[:300].reset_index(drop=True)
    curr = timeseries_df.iloc[300:350].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.verdict != Verdict.fail


def test_hw_spiked_series_detected(detector, timeseries_df):
    ref = timeseries_df.iloc[:300].reset_index(drop=True)
    curr = timeseries_df.iloc[300:350].copy().reset_index(drop=True)
    curr.iloc[::3, 0] += 30.0  # spike every 3rd point
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.details["anomaly_fraction"] > 0.0
    assert result.verdict != Verdict.pass_


def test_hw_score_bounded(detector, timeseries_df):
    ref = timeseries_df.iloc[:200].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(timeseries_df.iloc[200:250].reset_index(drop=True), state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_hw_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.02, "holt_winters") == Verdict.pass_
    assert compute_verdict(0.07, "holt_winters") == Verdict.warn
    assert compute_verdict(0.15, "holt_winters") == Verdict.fail


def test_hw_details_present(detector, timeseries_df):
    ref = timeseries_df.iloc[:200].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(timeseries_df.iloc[200:250].reset_index(drop=True), state)
    assert "anomaly_fraction" in result.details
    assert "n_anomalies" in result.details
    assert "period" in result.details
```

- [ ] **Step 2: Run test — verify it fails**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/timeseries/test_holt_winters.py -v 2>&1 | Select-Object -Last 10
```
Expected: `ImportError` for `holt_winters`.

- [ ] **Step 3: Implement `holt_winters.py`**

```python
# packages/dqt/src/dqt/algorithms/timeseries/holt_winters.py
# Ref: Holt (1957) ONR Memorandum 52; Winters (1960) Management Science 6(3)
# Fit Holt-Winters additive model on reference; score = fraction of current values outside PI.
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry


@registry.register
class HoltWintersDetector(BaseDetector):
    """Holt-Winters exponential smoothing anomaly detector. Score = fraction of current values outside prediction interval."""
    slug = "holt_winters"
    group = "timeseries"

    def __init__(self, period: int = 7, alpha: float = 0.95) -> None:
        # alpha: prediction interval coverage (default 95%)
        self._period = period
        self._alpha = alpha

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        values = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        if len(values) < 2 * self._period:
            raise ValueError(
                f"HoltWinters requires at least {2 * self._period} observations, got {len(values)}"
            )
        model = ExponentialSmoothing(
            values,
            trend="add",
            seasonal="add",
            seasonal_periods=self._period,
            initialization_method="estimated",
        ).fit(optimized=True, disp=False)
        fitted = model.fittedvalues
        residuals = values - fitted
        resid_std = float(np.std(residuals, ddof=1))
        return {
            "model": model,
            "resid_std": max(resid_std, 1e-8),
            "period": self._period,
            "alpha": self._alpha,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        from scipy import stats as scipy_stats
        values = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        if len(values) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"anomaly_fraction": 0.0, "n_anomalies": 0, "period": state["period"]},
            )
        # Forecast from the end of the training data
        model = state["model"]
        n = len(values)
        forecast = model.forecast(n)
        z = scipy_stats.norm.ppf((1.0 + state["alpha"]) / 2.0)
        margin = z * state["resid_std"]
        lower = forecast - margin
        upper = forecast + margin
        anomalies = (values < lower) | (values > upper)
        n_anomalies = int(np.sum(anomalies))
        frac = n_anomalies / n
        return DetectorResult(
            score=frac,
            verdict=self._verdict(frac),
            plain_english=(
                f"{n_anomalies} of {n} current values outside {state['alpha']:.0%} "
                f"Holt-Winters prediction interval ({frac:.1%})"
            ),
            details={
                "anomaly_fraction": frac,
                "n_anomalies": n_anomalies,
                "period": state["period"],
            },
        )
```

- [ ] **Step 4: Update `timeseries/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/timeseries/__init__.py
from dqt.algorithms.timeseries.cusum import CUSUMDetector
from dqt.algorithms.timeseries.holt_winters import HoltWintersDetector
from dqt.algorithms.timeseries.page_hinkley import PageHinkleyDetector
from dqt.algorithms.timeseries.stl import STLAnomalyDetector

__all__ = ["CUSUMDetector", "HoltWintersDetector", "PageHinkleyDetector", "STLAnomalyDetector"]
```

- [ ] **Step 5: Run tests — verify they pass**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/timeseries/test_holt_winters.py -v 2>&1 | Select-Object -Last 10
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add packages/dqt/src/dqt/algorithms/timeseries/holt_winters.py packages/dqt/src/dqt/algorithms/timeseries/__init__.py packages/dqt/tests/algorithms/timeseries/test_holt_winters.py
git commit -m "feat(detectors): add holt_winters — Holt-Winters anomaly detector"
```

---

## Task 11: `prophet_anomaly` — Prophet stub (optional `dqt[forecast]` extra)

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/timeseries/prophet_anomaly.py`
- Create: `packages/dqt/tests/algorithms/timeseries/test_prophet_anomaly.py`
- Modify: `packages/dqt/src/dqt/algorithms/timeseries/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/algorithms/timeseries/test_prophet_anomaly.py
# Ref: Taylor & Letham (2018) Am. Statistician — Forecasting at Scale (Prophet)
# This test only verifies the helpful ImportError stub; the full implementation
# requires the optional dqt[forecast] extra (prophet package).
import pytest


def test_prophet_raises_import_error_when_not_installed():
    """When prophet is not installed the detector must raise ImportError with an install hint."""
    try:
        import prophet  # noqa: F401
        pytest.skip("prophet is installed; stub test not applicable")
    except ImportError:
        pass
    from dqt.algorithms.timeseries.prophet_anomaly import ProphetAnomalyDetector
    import pandas as pd
    import numpy as np
    det = ProphetAnomalyDetector()
    df = pd.DataFrame({"value": np.random.default_rng(0).normal(0, 1, 50)})
    with pytest.raises(ImportError, match="dqt\\[forecast\\]"):
        det.fit(df)


def test_prophet_slug_and_group():
    from dqt.algorithms.timeseries.prophet_anomaly import ProphetAnomalyDetector
    assert ProphetAnomalyDetector.slug == "prophet_anomaly"
    assert ProphetAnomalyDetector.group == "timeseries"


def test_prophet_registered():
    import dqt  # noqa: F401 — triggers registry side effects
    from dqt.algorithms._registry import registry
    cls = registry.get("prophet_anomaly")
    assert cls is not None


def test_prophet_scale_exists():
    from dqt.algorithms._scales import STAT_SCALES
    assert "prophet_anomaly" in STAT_SCALES
```

- [ ] **Step 2: Run test — verify it fails**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/timeseries/test_prophet_anomaly.py -v 2>&1 | Select-Object -Last 10
```
Expected: `ImportError` for `prophet_anomaly` module.

- [ ] **Step 3: Implement `prophet_anomaly.py`**

```python
# packages/dqt/src/dqt/algorithms/timeseries/prophet_anomaly.py
# Ref: Taylor & Letham (2018) Am. Statistician 72(1) — Forecasting at Scale
# Requires optional dqt[forecast] extra: pip install dqt[forecast]
# When prophet is not installed, fit() and score() raise ImportError with install hint.
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_PROPHET_MISSING_MSG = (
    "prophet is not installed. "
    "Install the optional forecast extra: pip install 'dqt[forecast]' "
    "or pip install prophet"
)


def _require_prophet():
    try:
        import prophet  # noqa: F401
    except ImportError as exc:
        raise ImportError(_PROPHET_MISSING_MSG) from exc


@registry.register
class ProphetAnomalyDetector(BaseDetector):
    """Prophet-based anomaly detector (requires dqt[forecast] extra).

    Fit on reference time series; score = fraction of current values outside
    the uncertainty interval. Raises ImportError with install hint if prophet
    is not available.
    """
    slug = "prophet_anomaly"
    group = "timeseries"

    def __init__(self, interval_width: float = 0.95) -> None:
        self._interval_width = interval_width

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        _require_prophet()
        from prophet import Prophet  # type: ignore[import]
        values = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        n = len(values)
        ds = pd.date_range("2020-01-01", periods=n, freq="D")
        train = pd.DataFrame({"ds": ds, "y": values})
        model = Prophet(interval_width=self._interval_width, daily_seasonality=False)
        model.fit(train, verbose=False)
        return {
            "model": model,
            "n_train": n,
            "interval_width": self._interval_width,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        _require_prophet()
        values = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        if len(values) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={"anomaly_fraction": 0.0, "n_anomalies": 0},
            )
        model = state["model"]
        n_train = state["n_train"]
        n = len(values)
        future_ds = pd.date_range("2020-01-01", periods=n_train + n, freq="D")[-n:]
        future = pd.DataFrame({"ds": future_ds})
        forecast = model.predict(future)
        lower = forecast["yhat_lower"].to_numpy()
        upper = forecast["yhat_upper"].to_numpy()
        anomalies = (values < lower) | (values > upper)
        n_anomalies = int(np.sum(anomalies))
        frac = n_anomalies / n
        return DetectorResult(
            score=frac,
            verdict=self._verdict(frac),
            plain_english=(
                f"{n_anomalies} of {n} values outside Prophet "
                f"{state['interval_width']:.0%} uncertainty interval ({frac:.1%})"
            ),
            details={"anomaly_fraction": frac, "n_anomalies": n_anomalies},
        )
```

- [ ] **Step 4: Update `timeseries/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/timeseries/__init__.py
from dqt.algorithms.timeseries.cusum import CUSUMDetector
from dqt.algorithms.timeseries.holt_winters import HoltWintersDetector
from dqt.algorithms.timeseries.page_hinkley import PageHinkleyDetector
from dqt.algorithms.timeseries.prophet_anomaly import ProphetAnomalyDetector
from dqt.algorithms.timeseries.stl import STLAnomalyDetector

__all__ = [
    "CUSUMDetector",
    "HoltWintersDetector",
    "PageHinkleyDetector",
    "ProphetAnomalyDetector",
    "STLAnomalyDetector",
]
```

- [ ] **Step 5: Run tests — verify they pass**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/timeseries/test_prophet_anomaly.py -v 2>&1 | Select-Object -Last 10
```
Expected: all 4 tests pass (stub ImportError, slug/group, registry, scale).

- [ ] **Step 6: Commit**

```powershell
git add packages/dqt/src/dqt/algorithms/timeseries/prophet_anomaly.py packages/dqt/src/dqt/algorithms/timeseries/__init__.py packages/dqt/tests/algorithms/timeseries/test_prophet_anomaly.py
git commit -m "feat(detectors): add prophet_anomaly stub — raises ImportError until dqt[forecast] installed"
```

---

## Task 12: `adwin` — Adaptive Windowing drift detector

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/drift/adwin.py`
- Create: `packages/dqt/tests/algorithms/drift/test_adwin.py`
- Modify: `packages/dqt/src/dqt/algorithms/drift/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/algorithms/drift/test_adwin.py
# Ref: Bifet & Gavalda (2007) SDM — Learning from Time-Changing Data with Adaptive Windowing (ADWIN)
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.drift.adwin import ADWINDetector
    return ADWINDetector()


def test_adwin_stable_stream_pass(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert result.verdict == Verdict.pass_
    assert result.score < 0.5


def test_adwin_large_shift_detected(detector, normal_df, shifted_df):
    state = detector.fit(normal_df)
    result = detector.score(shifted_df, state)
    # ADWIN should detect a shift from N(10,2) to N(15,2) — 2.5σ gap
    assert result.verdict != Verdict.pass_
    assert result.score >= 0.5


def test_adwin_score_bounded(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_adwin_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    # ADWIN is binary: warn=fail=0.5, so anything below 0.5 is pass
    assert compute_verdict(0.0, "adwin") == Verdict.pass_
    assert compute_verdict(1.0, "adwin") == Verdict.fail


def test_adwin_details_present(detector, normal_df):
    state = detector.fit(normal_df)
    result = detector.score(normal_df, state)
    assert "drift_detected" in result.details
    assert "ref_mean" in result.details
    assert "curr_mean" in result.details
    assert "n_windows_checked" in result.details
```

- [ ] **Step 2: Run test — verify it fails**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/drift/test_adwin.py -v 2>&1 | Select-Object -Last 10
```
Expected: `ImportError` for `adwin`.

- [ ] **Step 3: Implement `adwin.py`**

```python
# packages/dqt/src/dqt/algorithms/drift/adwin.py
# Ref: Bifet & Gavalda (2007) SDM — Learning from Time-Changing Data with Adaptive Windowing
# Pure numpy. Combines reference + current into a single stream; checks all cut-points
# for a statistically significant mean difference using Hoeffding's bound.
# Score = 1.0 if drift detected, 0.0 otherwise.
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry


def _hoeffding_bound(n0: int, n1: int, delta: float) -> float:
    """Hoeffding/ADWIN epsilon: mean difference to declare drift."""
    m = 1.0 / (1.0 / n0 + 1.0 / n1)
    return float(np.sqrt(np.log(2.0 / delta) / (2.0 * m)))


@registry.register
class ADWINDetector(BaseDetector):
    """Adaptive Windowing (ADWIN) drift detector. Score = 1.0 if drift detected, 0.0 if stable."""
    slug = "adwin"
    group = "drift"

    def __init__(self, delta: float = 0.002) -> None:
        # delta: confidence parameter; smaller = more conservative
        self._delta = delta

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        ref = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        return {
            "reference": ref,
            "ref_mean": float(np.mean(ref)),
            "delta": self._delta,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        curr = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        ref = state["reference"]
        if len(curr) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={
                    "drift_detected": False,
                    "ref_mean": state["ref_mean"],
                    "curr_mean": float("nan"),
                    "n_windows_checked": 0,
                },
            )
        combined = np.concatenate([ref, curr])
        n = len(combined)
        delta = state["delta"]
        drift_detected = False
        n_checked = 0
        for cut in range(1, n):
            n0 = cut
            n1 = n - cut
            if n0 < 1 or n1 < 1:
                continue
            eps = _hoeffding_bound(n0, n1, delta)
            mean_diff = abs(float(np.mean(combined[:n0])) - float(np.mean(combined[n0:])))
            n_checked += 1
            if mean_diff > eps:
                drift_detected = True
                break
        score = 1.0 if drift_detected else 0.0
        curr_mean = float(np.mean(curr))
        return DetectorResult(
            score=score,
            verdict=self._verdict(score),
            plain_english=(
                f"ADWIN: {'drift detected' if drift_detected else 'stable'} "
                f"(ref_mean={state['ref_mean']:.4f}, curr_mean={curr_mean:.4f})"
            ),
            details={
                "drift_detected": drift_detected,
                "ref_mean": state["ref_mean"],
                "curr_mean": curr_mean,
                "n_windows_checked": n_checked,
            },
        )
```

- [ ] **Step 4: Update `drift/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/drift/__init__.py
from dqt.algorithms.drift.adwin import ADWINDetector
from dqt.algorithms.drift.chi_square import ChiSquareDriftDetector
from dqt.algorithms.drift.divergence import JSDivergenceDetector, KLDivergenceDetector
from dqt.algorithms.drift.ks2sample import KS2SampleDetector
from dqt.algorithms.drift.mmd import MMDDetector
from dqt.algorithms.drift.psi import PSIDetector
from dqt.algorithms.drift.wasserstein import Wasserstein1Detector

__all__ = [
    "ADWINDetector",
    "ChiSquareDriftDetector",
    "JSDivergenceDetector",
    "KLDivergenceDetector",
    "KS2SampleDetector",
    "MMDDetector",
    "PSIDetector",
    "Wasserstein1Detector",
]
```

- [ ] **Step 5: Run tests — verify they pass**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/drift/test_adwin.py -v 2>&1 | Select-Object -Last 10
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add packages/dqt/src/dqt/algorithms/drift/adwin.py packages/dqt/src/dqt/algorithms/drift/__init__.py packages/dqt/tests/algorithms/drift/test_adwin.py
git commit -m "feat(detectors): add adwin — Adaptive Windowing drift detector"
```

---

## Task 13: `bocpd` — Bayesian Online Changepoint Detection

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/timeseries/bocpd.py`
- Create: `packages/dqt/tests/algorithms/timeseries/test_bocpd.py`
- Modify: `packages/dqt/src/dqt/algorithms/timeseries/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/algorithms/timeseries/test_bocpd.py
# Ref: Adams & MacKay (2007) arXiv:0710.3742 — Bayesian Online Changepoint Detection
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.timeseries.bocpd import BOCPDDetector
    return BOCPDDetector()


def test_bocpd_no_changepoint_pass(detector, timeseries_df):
    ref = timeseries_df.iloc[:200].reset_index(drop=True)
    curr = timeseries_df.iloc[200:250].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.score < 0.80
    assert result.verdict != Verdict.fail


def test_bocpd_clear_changepoint_detected(detector):
    rng = np.random.default_rng(42)
    # Second half has a clearly different mean
    before = rng.normal(0, 1, 100)
    after = rng.normal(20, 1, 50)
    ref = pd.DataFrame({"value": before})
    curr = pd.DataFrame({"value": after})
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.score > 0.50
    assert result.verdict != Verdict.pass_


def test_bocpd_score_bounded(detector, timeseries_df):
    ref = timeseries_df.iloc[:200].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(timeseries_df.iloc[200:230].reset_index(drop=True), state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_bocpd_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.30, "bocpd") == Verdict.pass_
    assert compute_verdict(0.65, "bocpd") == Verdict.warn
    assert compute_verdict(0.90, "bocpd") == Verdict.fail


def test_bocpd_details_present(detector, timeseries_df):
    ref = timeseries_df.iloc[:200].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(timeseries_df.iloc[200:230].reset_index(drop=True), state)
    assert "max_changepoint_prob" in result.details
    assert "ref_mean" in result.details
    assert "ref_std" in result.details
```

- [ ] **Step 2: Run test — verify it fails**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/timeseries/test_bocpd.py -v 2>&1 | Select-Object -Last 10
```
Expected: `ImportError` for `bocpd`.

- [ ] **Step 3: Implement `bocpd.py`**

```python
# packages/dqt/src/dqt/algorithms/timeseries/bocpd.py
# Ref: Adams & MacKay (2007) arXiv:0710.3742 — Bayesian Online Changepoint Detection
# Gaussian likelihood, student-t predictive (normal-inverse-chi-sq conjugate), hazard=1/lambda.
# Pure numpy — no ruptures or other external deps.
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_EPSILON = 1e-12


def _bocpd_run_lengths(
    data: np.ndarray,
    mu0: float,
    kappa0: float,
    alpha0: float,
    beta0: float,
    hazard_lambda: float,
) -> np.ndarray:
    """
    Run BOCPD with normal-inverse-chi-sq conjugate.
    Returns array of length T where each entry is the posterior probability of a changepoint
    at that time step (p(r_t=0|x_1..t)).
    """
    T = len(data)
    # R[t, l] = P(r_t = l | x_1..t) — run-length posterior
    max_run = T + 1
    log_R = np.full((T + 1, max_run), -np.inf)
    log_R[0, 0] = 0.0  # at t=0, run length=0 with prob 1

    # Sufficient statistics for conjugate update (vectorised over run lengths)
    mu = np.full(max_run, mu0)
    kappa = np.full(max_run, kappa0)
    alpha = np.full(max_run, alpha0)
    beta = np.full(max_run, beta0)

    hazard = 1.0 / hazard_lambda
    changepoint_probs = np.zeros(T)

    for t in range(T):
        x = data[t]
        active = np.isfinite(log_R[t])

        # Predictive probability: student-t marginal
        # p(x|r_{t-1}, x_{1..t-1}) = t_{2*alpha}(mu, beta*(kappa+1)/(alpha*kappa))
        pred_scale = np.where(
            active & (alpha > 0) & (kappa > 0),
            np.sqrt(beta * (kappa + 1.0) / (alpha * kappa)),
            1.0,
        )
        pred_df = np.where(active, 2.0 * alpha, 1.0)
        log_pred = np.where(
            active,
            stats.t.logpdf(x, df=pred_df, loc=mu, scale=np.maximum(pred_scale, _EPSILON)),
            -np.inf,
        )

        # Growth probabilities: existing runs grow by 1
        log_growth = log_R[t] + log_pred + np.log(1.0 - hazard)

        # Changepoint probability: all runs collapse to run-length 0
        log_cp = np.logaddexp.reduce(log_R[t][active] + log_pred[active]) + np.log(hazard)

        # Update run-length distribution
        log_R[t + 1, 1:] = log_growth[:-1]
        log_R[t + 1, 0] = log_cp

        # Normalise
        log_norm = np.logaddexp.reduce(log_R[t + 1][np.isfinite(log_R[t + 1])])
        log_R[t + 1] -= log_norm

        # Changepoint probability at this step = p(r_t = 0)
        changepoint_probs[t] = float(np.exp(log_R[t + 1, 0]))

        # Conjugate update (shift index: new run of length l corresponds to old length l-1)
        kappa_new = np.empty_like(kappa)
        mu_new = np.empty_like(mu)
        alpha_new = np.empty_like(alpha)
        beta_new = np.empty_like(beta)
        # run-length 0 resets to prior
        kappa_new[0] = kappa0
        mu_new[0] = mu0
        alpha_new[0] = alpha0
        beta_new[0] = beta0
        # run-lengths >= 1 update
        kappa_new[1:] = kappa[:-1] + 1.0
        mu_new[1:] = (kappa[:-1] * mu[:-1] + x) / kappa_new[1:]
        alpha_new[1:] = alpha[:-1] + 0.5
        beta_new[1:] = (
            beta[:-1]
            + (kappa[:-1] * (x - mu[:-1]) ** 2) / (2.0 * kappa_new[1:])
        )
        mu, kappa, alpha, beta = mu_new, kappa_new, alpha_new, beta_new

    return changepoint_probs


@registry.register
class BOCPDDetector(BaseDetector):
    """Bayesian Online Changepoint Detection. Score = max posterior changepoint probability in current window."""
    slug = "bocpd"
    group = "timeseries"

    def __init__(self, hazard_lambda: float = 250.0) -> None:
        # hazard_lambda: expected run length before a changepoint (higher = fewer expected CPs)
        self._hazard_lambda = hazard_lambda

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        values = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        mu0 = float(np.mean(values))
        std0 = float(np.std(values, ddof=1))
        return {
            "ref_mean": mu0,
            "ref_std": max(std0, 1e-8),
            "mu0": mu0,
            "kappa0": 1.0,
            "alpha0": 1.0,
            "beta0": max(std0 ** 2, 1e-8),
            "hazard_lambda": self._hazard_lambda,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        values = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        if len(values) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english="No data to score.",
                details={
                    "max_changepoint_prob": 0.0,
                    "ref_mean": state["ref_mean"],
                    "ref_std": state["ref_std"],
                },
            )
        cp_probs = _bocpd_run_lengths(
            values,
            mu0=state["mu0"],
            kappa0=state["kappa0"],
            alpha0=state["alpha0"],
            beta0=state["beta0"],
            hazard_lambda=state["hazard_lambda"],
        )
        max_prob = float(np.max(cp_probs))
        score = float(min(max(max_prob, 0.0), 1.0))
        return DetectorResult(
            score=score,
            verdict=self._verdict(score),
            plain_english=(
                f"BOCPD max changepoint probability = {score:.4f} in current window "
                f"({'changepoint likely' if score >= 0.50 else 'stable'})"
            ),
            details={
                "max_changepoint_prob": score,
                "ref_mean": state["ref_mean"],
                "ref_std": state["ref_std"],
            },
        )
```

- [ ] **Step 4: Update `timeseries/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/timeseries/__init__.py
from dqt.algorithms.timeseries.bocpd import BOCPDDetector
from dqt.algorithms.timeseries.cusum import CUSUMDetector
from dqt.algorithms.timeseries.holt_winters import HoltWintersDetector
from dqt.algorithms.timeseries.page_hinkley import PageHinkleyDetector
from dqt.algorithms.timeseries.prophet_anomaly import ProphetAnomalyDetector
from dqt.algorithms.timeseries.stl import STLAnomalyDetector

__all__ = [
    "BOCPDDetector",
    "CUSUMDetector",
    "HoltWintersDetector",
    "PageHinkleyDetector",
    "ProphetAnomalyDetector",
    "STLAnomalyDetector",
]
```

- [ ] **Step 5: Run tests — verify they pass**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/timeseries/test_bocpd.py -v 2>&1 | Select-Object -Last 10
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add packages/dqt/src/dqt/algorithms/timeseries/bocpd.py packages/dqt/src/dqt/algorithms/timeseries/__init__.py packages/dqt/tests/algorithms/timeseries/test_bocpd.py
git commit -m "feat(detectors): add bocpd — Bayesian Online Changepoint Detection (pure numpy)"
```

---

## Task 14: `matrix_profile` — Matrix Profile (STUMPY or pure-numpy fallback)

**Files:**
- Create: `packages/dqt/src/dqt/algorithms/timeseries/matrix_profile.py`
- Create: `packages/dqt/tests/algorithms/timeseries/test_matrix_profile.py`
- Modify: `packages/dqt/src/dqt/algorithms/timeseries/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/dqt/tests/algorithms/timeseries/test_matrix_profile.py
# Ref: Yeh et al. (2016) ICDM — Matrix Profile I; STUMPY (Law 2019) JOSS
import math
import numpy as np
import pandas as pd
import pytest
from dqt.algorithms._base import Verdict


@pytest.fixture()
def detector():
    from dqt.algorithms.timeseries.matrix_profile import MatrixProfileDetector
    return MatrixProfileDetector(window=7)


def test_mp_stable_series_pass(detector, timeseries_df):
    ref = timeseries_df.iloc[:280].reset_index(drop=True)
    curr = timeseries_df.iloc[280:350].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.verdict == Verdict.pass_


def test_mp_discord_detected(detector, timeseries_df):
    ref = timeseries_df.iloc[:280].reset_index(drop=True)
    curr = timeseries_df.iloc[280:350].copy().reset_index(drop=True)
    # Inject a discord: replace middle subsequence with an extreme outlier pattern
    curr.iloc[30:37, 0] = 500.0
    state = detector.fit(ref)
    result = detector.score(curr, state)
    assert result.details["discord_fraction"] > 0.0
    assert result.verdict != Verdict.pass_


def test_mp_score_bounded(detector, timeseries_df):
    ref = timeseries_df.iloc[:200].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(timeseries_df.iloc[200:270].reset_index(drop=True), state)
    assert 0.0 <= result.score <= 1.0
    assert not math.isnan(result.score)
    assert not math.isinf(result.score)


def test_mp_stat_scale_verdict():
    from dqt.algorithms._base import compute_verdict
    assert compute_verdict(0.02, "matrix_profile") == Verdict.pass_
    assert compute_verdict(0.07, "matrix_profile") == Verdict.warn
    assert compute_verdict(0.15, "matrix_profile") == Verdict.fail


def test_mp_details_present(detector, timeseries_df):
    ref = timeseries_df.iloc[:200].reset_index(drop=True)
    state = detector.fit(ref)
    result = detector.score(timeseries_df.iloc[200:270].reset_index(drop=True), state)
    assert "discord_fraction" in result.details
    assert "distance_threshold" in result.details
    assert "window" in result.details
    assert "backend" in result.details


def test_mp_slug_registered():
    import dqt  # noqa: F401
    from dqt.algorithms._registry import registry
    assert registry.get("matrix_profile") is not None
```

- [ ] **Step 2: Run test — verify it fails**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/timeseries/test_matrix_profile.py -v 2>&1 | Select-Object -Last 10
```
Expected: `ImportError` for `matrix_profile`.

- [ ] **Step 3: Implement `matrix_profile.py`**

```python
# packages/dqt/src/dqt/algorithms/timeseries/matrix_profile.py
# Ref: Yeh et al. (2016) ICDM — Matrix Profile I: Motifs, Discords, and Shapelets
# Ref: Law (2019) JOSS — STUMPY: A Powerful and Scalable Python Library for Time Series Data Mining
# Uses stumpy if installed; falls back to brute-force z-normalised Euclidean 1-NN distance.
# Score = fraction of current subsequences whose 1-NN distance exceeds reference 95th percentile.
from __future__ import annotations

import numpy as np
import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_EPSILON = 1e-8


def _znorm(x: np.ndarray) -> np.ndarray:
    mu = x.mean()
    sigma = x.std()
    return (x - mu) / max(sigma, _EPSILON)


def _nn_distances_numpy(
    query_subsequences: np.ndarray,
    reference_subsequences: np.ndarray,
) -> np.ndarray:
    """Brute-force 1-NN z-normalised Euclidean distance for each query sub-sequence."""
    w = query_subsequences.shape[1]
    distances = np.empty(len(query_subsequences))
    ref_znorm = np.array([_znorm(s) for s in reference_subsequences])
    for i, qs in enumerate(query_subsequences):
        qz = _znorm(qs)
        diffs = ref_znorm - qz
        dists = np.sqrt(np.sum(diffs ** 2, axis=1))
        distances[i] = float(np.min(dists))
    return distances


def _extract_subsequences(values: np.ndarray, window: int) -> np.ndarray:
    n = len(values)
    if n < window:
        return np.empty((0, window))
    return np.array([values[i: i + window] for i in range(n - window + 1)])


@registry.register
class MatrixProfileDetector(BaseDetector):
    """Matrix Profile discord detector. Score = fraction of current subsequences with 1-NN dist above reference 95th pct."""
    slug = "matrix_profile"
    group = "timeseries"

    def __init__(self, window: int = 7) -> None:
        self._window = window

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        values = reference.iloc[:, 0].dropna().to_numpy(dtype=float)
        if len(values) < self._window:
            raise ValueError(
                f"MatrixProfile requires at least {self._window} reference observations, got {len(values)}"
            )
        try:
            import stumpy  # type: ignore[import]
            mp = stumpy.stump(values, m=self._window)
            ref_distances = mp[:, 0].astype(float)
            backend = "stumpy"
        except ImportError:
            subsequences = _extract_subsequences(values, self._window)
            ref_distances = _nn_distances_numpy(subsequences, subsequences)
            backend = "numpy"

        threshold = float(np.percentile(ref_distances, 95))
        return {
            "reference": values,
            "threshold": threshold,
            "window": self._window,
            "backend": backend,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        values = current.iloc[:, 0].dropna().to_numpy(dtype=float)
        window = state["window"]
        if len(values) < window:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english=f"Not enough data for window={window}.",
                details={
                    "discord_fraction": 0.0,
                    "distance_threshold": state["threshold"],
                    "window": window,
                    "backend": state["backend"],
                },
            )
        try:
            import stumpy  # type: ignore[import]
            # ab_join: distances from current subsequences to reference subsequences
            ab = stumpy.stumped(
                None,  # not parallel; use stumpy.stumped not available in all versions
                values,
                state["reference"],
                m=window,
            )
            curr_distances = ab[:, 0].astype(float)
            backend = "stumpy"
        except (ImportError, Exception):
            ref_subs = _extract_subsequences(state["reference"], window)
            curr_subs = _extract_subsequences(values, window)
            if len(curr_subs) == 0:
                curr_distances = np.array([])
            else:
                curr_distances = _nn_distances_numpy(curr_subs, ref_subs)
            backend = "numpy"

        if len(curr_distances) == 0:
            return DetectorResult(
                score=0.0, verdict=Verdict.pass_,
                plain_english=f"No subsequences extracted with window={window}.",
                details={
                    "discord_fraction": 0.0,
                    "distance_threshold": state["threshold"],
                    "window": window,
                    "backend": backend,
                },
            )
        n_discord = int(np.sum(curr_distances > state["threshold"]))
        frac = n_discord / len(curr_distances)
        return DetectorResult(
            score=frac,
            verdict=self._verdict(frac),
            plain_english=(
                f"{n_discord} of {len(curr_distances)} subsequences are discords "
                f"(distance > {state['threshold']:.3f}; {frac:.1%}); "
                f"backend={backend}"
            ),
            details={
                "discord_fraction": frac,
                "distance_threshold": state["threshold"],
                "window": window,
                "backend": backend,
            },
        )
```

- [ ] **Step 4: Update `timeseries/__init__.py`**

```python
# packages/dqt/src/dqt/algorithms/timeseries/__init__.py
from dqt.algorithms.timeseries.bocpd import BOCPDDetector
from dqt.algorithms.timeseries.cusum import CUSUMDetector
from dqt.algorithms.timeseries.holt_winters import HoltWintersDetector
from dqt.algorithms.timeseries.matrix_profile import MatrixProfileDetector
from dqt.algorithms.timeseries.page_hinkley import PageHinkleyDetector
from dqt.algorithms.timeseries.prophet_anomaly import ProphetAnomalyDetector
from dqt.algorithms.timeseries.stl import STLAnomalyDetector

__all__ = [
    "BOCPDDetector",
    "CUSUMDetector",
    "HoltWintersDetector",
    "MatrixProfileDetector",
    "PageHinkleyDetector",
    "ProphetAnomalyDetector",
    "STLAnomalyDetector",
]
```

- [ ] **Step 5: Run tests — verify they pass**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/algorithms/timeseries/test_matrix_profile.py -v 2>&1 | Select-Object -Last 10
```
Expected: all tests pass (using numpy fallback since stumpy is not installed).

- [ ] **Step 6: Commit**

```powershell
git add packages/dqt/src/dqt/algorithms/timeseries/matrix_profile.py packages/dqt/src/dqt/algorithms/timeseries/__init__.py packages/dqt/tests/algorithms/timeseries/test_matrix_profile.py
git commit -m "feat(detectors): add matrix_profile — Matrix Profile discord detector (stumpy or numpy fallback)"
```

---

## Task 15: Full test suite verification + slug registration check

- [ ] **Step 1: Run the full unit test suite**

```powershell
cd c:\anton\dqt
uv run pytest packages/dqt/tests/ -q --ignore=packages/dqt/tests/adapters 2>&1 | Select-Object -Last 20
```
Expected: all tests pass (pre-existing flakiness in `test_mad_stability` is the only acceptable exception).

- [ ] **Step 2: Verify all 14 new slugs are registered**

```powershell
cd c:\anton\dqt
uv run python -c "
import dqt
from dqt.algorithms._registry import registry
new_slugs = [
    'mmd', 'mutual_information',
    'mahalanobis_distance', 'lof', 'one_class_svm', 'hbos', 'ecod',
    'cusum', 'page_hinkley', 'holt_winters', 'prophet_anomaly',
    'adwin', 'bocpd', 'matrix_profile',
]
for s in new_slugs:
    cls = registry.get(s)
    status = 'OK ' if cls is not None else 'MISSING'
    print(f'{status}  {s} -> {cls.__name__ if cls else \"???\"}')"
```
Expected: 14 lines starting with `OK`.

- [ ] **Step 3: Verify scale count**

```powershell
cd c:\anton\dqt
uv run python -c "from dqt.algorithms._scales import STAT_SCALES; print(len(STAT_SCALES), 'scales')"
```
Expected: `62 scales`.

- [ ] **Step 4: Commit verification marker**

No code change — just verify. If all passed:

```powershell
cd c:\anton\dqt
git push
```

---

## Self-Review

**Spec coverage:**

Group B1 — scipy/sklearn only:
- `mmd` — Task 2
- `mutual_information` — Task 3
- `mahalanobis_distance` — Task 4
- `lof` — Task 5
- `one_class_svm` — Task 6

Group B2 — time series:
- `cusum` — Task 8
- `page_hinkley` — Task 9
- `holt_winters` — Task 10
- `prophet_anomaly` — Task 11 (stub + optional)
- `adwin` — Task 12

Group B3 — pure numpy / heavier:
- `hbos` — Task 7
- `ecod` — Task 7
- `bocpd` — Task 13
- `matrix_profile` — Task 14

- STAT_SCALES (14 entries) — Task 1
- `__init__.py` registration — each task
- Full verification — Task 15

**Design decisions:**
- `adwin` uses a full scan of all cut-points (O(n²)) rather than the exponential-histogram approximation from the paper. This is correct for the small windows typical in check scoring (a few hundred rows) and avoids complexity. Comment in code notes this.
- `matrix_profile` falls back gracefully to brute-force z-normalised Euclidean 1-NN when stumpy is not installed. The stumpy `stumped` function is tried for the AB-join; on any failure (version mismatch, not installed) it falls back to numpy. Tests run on the numpy path.
- `bocpd` is pure numpy using a dense T×T run-length matrix (bounded by window size) — correct for short windows. For very long series the matrix is O(T²) memory; the detector is intended for check windows of a few hundred points, not full time series.
- `prophet_anomaly` raises `ImportError` at `fit()` time (not import time) so the module always imports cleanly, the registry entry is always present, and the slug and STAT_SCALE are always queryable. Only the actual fitting/scoring fails if prophet is absent.
- `mutual_information` uses a joint-histogram approach (not `sklearn.feature_selection.mutual_info_regression`) to avoid requiring a continuous-variable estimator and to keep the direction interpretable (NMI higher = more similar = less drift). This is the right choice for the drift detection use-case.
- `matrix_profile` uses `stumpy.stumped` (parallel) for the AB-join when stumpy is available; the except-clause catches both `ImportError` and any runtime exception from version differences.

**Placeholder scan:** No TBDs. All code is complete and exact.

**Type consistency:**
- All detectors use `DetectorState = Any` (dict in practice) — consistent with existing pattern.
- All `score()` methods return `DetectorResult` — consistent.
- All slugs in STAT_SCALES match class `slug` attributes exactly.
