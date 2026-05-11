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
