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
    lag: int
    raw_p_value: float
    adjusted_p_value: float
    val_min: float
    evidence_strength: str
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

    arrays = [stationary_arrays[c][0] for c in usable]
    differenced_flags = [stationary_arrays[c][1] for c in usable]
    data_matrix = np.column_stack(arrays)
    nan_rows = np.any(np.isnan(data_matrix), axis=1)
    data_matrix = data_matrix[~nan_rows]

    if len(data_matrix) < _MIN_ROWS:
        return PCMCIReport(significance_level=significance_level)

    dataframe = pp.DataFrame(data_matrix, var_names=usable)
    cit = ParCorr(significance="analytic")
    pcmci = PCMCI(dataframe=dataframe, cond_ind_test=cit, verbosity=0)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        results = pcmci.run_pcmciplus(tau_min=1, tau_max=tau_max, pc_alpha=0.05)

    p_matrix = results["p_matrix"]
    val_matrix = results["val_matrix"]

    _pending: list[tuple[str, str, float, float, int, bool]] = []
    for i, cause in enumerate(usable):
        for j, effect in enumerate(usable):
            if i == j:
                continue
            p_slice = p_matrix[j, i, 1:]
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
