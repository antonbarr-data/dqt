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


def test_pcmci_multivariate_no_direction_reversal():
    """3-variable chain x→y→z: significant edges must have correct direction."""
    pytest.importorskip("tigramite")
    from dqt.causality.pcmci import pcmci_pairwise

    rng = np.random.default_rng(7)
    n = 300
    x = rng.normal(0, 1, n)
    y = 0.8 * np.roll(x, 1) + rng.normal(0, 0.2, n)
    z = 0.8 * np.roll(y, 1) + rng.normal(0, 0.2, n)
    y[0] = 0.0
    z[0] = 0.0

    df = pd.DataFrame({"x": x, "y": y, "z": z})
    report = pcmci_pairwise(df, tau_max=3)

    sig = {(e.cause, e.effect) for e in report.edges if e.significant}

    # Correct direction: x→y and y→z must be found
    assert ("x", "y") in sig, f"Expected x→y in sig, got: {sig}"
    assert ("y", "z") in sig, f"Expected y→z in sig, got: {sig}"

    # Reversed directions must NOT be the only significant edges
    # (the bug caused all edges to be reversed)
    assert ("y", "x") not in sig or ("x", "y") in sig, \
        f"Reversed edge y→x found but not forward x→y: {sig}"


@pytest.mark.unit
def test_pcmci_raises_without_tigramite(monkeypatch):
    """ImportError if tigramite not installed."""
    import importlib
    import sys

    monkeypatch.setitem(sys.modules, "tigramite", None)
    monkeypatch.setitem(sys.modules, "tigramite.data_processing", None)
    monkeypatch.setitem(sys.modules, "tigramite.pcmci", None)
    monkeypatch.setitem(sys.modules, "tigramite.independence_tests.parcorr", None)
    with pytest.raises((ImportError, TypeError)):
        import dqt.causality.pcmci as pcmci_mod

        importlib.reload(pcmci_mod)
        pcmci_mod.pcmci_pairwise(pd.DataFrame({"a": [1.0, 2.0, 3.0]}))
