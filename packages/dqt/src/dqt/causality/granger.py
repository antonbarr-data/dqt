# packages/dqt/src/dqt/causality/granger.py
# Ref: Granger (1969) Econometrica 37(3) — Investigating Causal Relations by Econometric Models
# Bivariate Granger causality: does X lag-k help predict Y beyond Y's own lags?
# Uses statsmodels grangercausalitytests (F-test, OLS).
# B1: ADF stationarity gate with one auto-diff.
# B2: Benjamini-Hochberg FDR correction across all tested pairs.
# B3: AIC-based lag selection via VAR instead of min-p across all lags.
# B4: Confounder annotation — flags Z s.t. Z→X and Z→Y are both significant.
# B5: Evidence-strength tiers ("none" / "weak" / "moderate" / "strong").
from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

_MIN_ROWS = 20
_ADF_ALPHA = 0.05  # stationarity significance level


# ---------------------------------------------------------------------------
# Stationarity helpers (B1)
# ---------------------------------------------------------------------------

def _is_stationary(series: np.ndarray) -> bool:
    """Return True if ADF rejects the unit-root null at _ADF_ALPHA."""
    from statsmodels.tsa.stattools import adfuller
    clean = series[~np.isnan(series)]
    if len(clean) < 8:
        return True  # too short to test — treat as stationary to avoid skip
    result = adfuller(clean, autolag="AIC")
    return float(result[1]) <= _ADF_ALPHA


def _make_stationary(series: np.ndarray) -> tuple[np.ndarray, bool]:
    """Return (series, differenced).

    If already stationary: (series, False).
    After one diff: (differenced_series, True) — first element is NaN.
    If still non-stationary after one diff: raises _NonStationaryError.
    """
    if _is_stationary(series):
        return series, False
    diffed = np.concatenate([[np.nan], np.diff(series)])
    if _is_stationary(diffed):
        return diffed, True
    raise _NonStationaryError()


class _NonStationaryError(Exception):
    """Series is integrated of order > 1; skip Granger test."""


# ---------------------------------------------------------------------------
# AIC lag selection (B3)
# ---------------------------------------------------------------------------

def _select_lag_aic(y: np.ndarray, x: np.ndarray, max_lag: int) -> int:
    """Fit VAR([y, x], maxlags=max_lag, ic='aic') and return the AIC-optimal lag.

    Falls back to lag=1 if VAR fitting fails for any reason.
    """
    from statsmodels.tsa.vector_ar.var_model import VAR
    data = np.column_stack([y, x])
    valid = ~np.any(np.isnan(data), axis=1)
    data = data[valid]
    if len(data) < max_lag * 2 + 2:
        return 1
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = VAR(data)
            result = model.fit(maxlags=max_lag, ic="aic", verbose=False)
            return max(1, int(result.k_ar))
    except Exception:
        return 1


# ---------------------------------------------------------------------------
# BH-FDR correction (B2)
# ---------------------------------------------------------------------------

def _bh_correction(p_values: list[float]) -> list[float]:
    """Benjamini-Hochberg FDR correction; returns adjusted p-values in input order."""
    n = len(p_values)
    if n == 0:
        return []
    # scipy >= 1.11 has false_discovery_control; fall back to manual BH otherwise
    try:
        from scipy.stats import false_discovery_control
        return list(false_discovery_control(np.array(p_values), method="bh"))
    except ImportError:
        pass
    # Manual BH
    order = np.argsort(p_values)
    ranks = np.empty(n, dtype=int)
    ranks[order] = np.arange(1, n + 1)
    adjusted = np.minimum(1.0, np.array(p_values) * n / ranks)
    # Enforce monotonicity (isotonic step)
    for i in range(n - 2, -1, -1):
        if adjusted[order[i]] > adjusted[order[i + 1]]:
            adjusted[order[i]] = adjusted[order[i + 1]]
    return list(adjusted)


# ---------------------------------------------------------------------------
# Evidence strength tier (B5)
# ---------------------------------------------------------------------------

def _evidence_strength(adjusted_p: float) -> str:
    if adjusted_p < 0.01:
        return "strong"
    if adjusted_p < 0.05:
        return "moderate"
    if adjusted_p < 0.1:
        return "weak"
    return "none"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class GrangerEdge:
    """Result of a single X → Y Granger causality test."""
    cause: str
    effect: str
    max_lag: int
    selected_lag: int         # AIC-selected lag (B3)
    raw_p_value: float        # p at selected lag, before correction (B2)
    adjusted_p_value: float   # BH-corrected p-value (B2)
    f_statistic: float
    evidence_strength: str    # "none" | "weak" | "moderate" | "strong" (B5)
    differenced: bool         # True if series was auto-differenced (B1)
    confounder_candidates: list[str] = field(default_factory=list)  # B4

    @property
    def significant(self) -> bool:
        return self.evidence_strength in ("moderate", "strong")


@dataclass
class GrangerReport:
    """Pairwise Granger causality report for a panel of time series."""
    edges: list[GrangerEdge] = field(default_factory=list)
    significance_level: float = 0.05

    @property
    def significant_edges(self) -> list[GrangerEdge]:
        return [e for e in self.edges if e.significant]

    def to_dict(self) -> dict:
        return {
            "n_pairs_tested": len(self.edges),
            "n_significant": len(self.significant_edges),
            "significance_level": self.significance_level,
            "edges": [
                {
                    "cause": e.cause,
                    "effect": e.effect,
                    "selected_lag": e.selected_lag,
                    "raw_p_value": e.raw_p_value,
                    "adjusted_p_value": e.adjusted_p_value,
                    "f_statistic": e.f_statistic,
                    "evidence_strength": e.evidence_strength,
                    "significant": e.significant,
                    "differenced": e.differenced,
                    "confounder_candidates": e.confounder_candidates,
                }
                for e in self.edges
            ],
        }


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def granger_pairwise(
    df: pd.DataFrame,
    max_lag: int = 4,
    significance_level: float = 0.05,
    columns: list[str] | None = None,
) -> GrangerReport:
    """Run bivariate Granger causality for every ordered (X, Y) pair in df.

    Parameters
    ----------
    df:
        DataFrame where each column is a time series (rows = time steps).
        Must have at least ``max_lag * 2 + 1`` rows.
    max_lag:
        Maximum lag to consider. AIC selects the optimal lag within 1..max_lag.
    significance_level:
        p-value threshold for declaring an edge significant (applied to
        BH-adjusted p-values).
    columns:
        Subset of columns to test. Defaults to all numeric columns.

    Returns
    -------
    GrangerReport with one GrangerEdge per ordered pair that could be tested.

    Example
    -------
    Gigler marketplace: does ``gig_views`` Granger-cause ``bookings``?

    >>> import pandas as pd, numpy as np
    >>> rng = np.random.default_rng(42)
    >>> n = 100
    >>> gig_views = rng.normal(1000, 100, n)
    >>> bookings = 0.3 * np.roll(gig_views, 2) + rng.normal(50, 10, n)
    >>> df = pd.DataFrame({"gig_views": gig_views, "bookings": bookings})
    >>> report = granger_pairwise(df, max_lag=3)
    >>> print(report.significant_edges[0].cause, "->", report.significant_edges[0].effect)
    gig_views -> bookings
    """
    from statsmodels.tsa.stattools import grangercausalitytests

    if columns is None:
        columns = list(df.select_dtypes(include="number").columns)

    if len(df) < _MIN_ROWS:
        raise ValueError(f"granger_pairwise requires at least {_MIN_ROWS} rows, got {len(df)}")

    report = GrangerReport(significance_level=significance_level)

    # --- B1: pre-compute stationary series for each column --------------------
    stationary: dict[str, tuple[np.ndarray, bool]] = {}
    non_stationary_cols: set[str] = set()
    for col in columns:
        raw = df[col].to_numpy(dtype=float)
        try:
            stationary[col] = _make_stationary(raw)
        except _NonStationaryError:
            non_stationary_cols.add(col)

    # --- Collect raw (cause, effect, raw_p, f_stat, selected_lag, differenced) --
    # We need all raw p-values before BH correction, so accumulate in a list first.
    _pending: list[tuple[str, str, float, float, int, bool]] = []

    for cause in columns:
        if cause in non_stationary_cols:
            continue
        x_series, x_diff = stationary[cause]

        for effect in columns:
            if cause == effect:
                continue
            if effect in non_stationary_cols:
                continue
            y_series, y_diff = stationary[effect]

            # Align and drop NaNs (differenced series has a leading NaN)
            data_df = pd.DataFrame({"y": y_series, "x": x_series}).dropna()
            if len(data_df) < max_lag * 2 + 2:
                continue

            y_arr = data_df["y"].to_numpy(dtype=float)
            x_arr = data_df["x"].to_numpy(dtype=float)

            # B3: AIC lag selection
            selected_lag = _select_lag_aic(y_arr, x_arr, max_lag)

            # Run Granger test at the single AIC-selected lag
            data_arr = np.column_stack([y_arr, x_arr])
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", FutureWarning)
                    results = grangercausalitytests(
                        data_arr, maxlag=selected_lag, verbose=False
                    )
            except Exception:
                continue

            p_val = float(results[selected_lag][0]["ssr_ftest"][1])
            f_stat = float(results[selected_lag][0]["ssr_ftest"][0])
            differenced = x_diff or y_diff

            _pending.append((cause, effect, p_val, f_stat, selected_lag, differenced))

    # --- B2: BH correction across all tested pairs ---------------------------
    raw_ps = [item[2] for item in _pending]
    adjusted_ps = _bh_correction(raw_ps)

    for (cause, effect, raw_p, f_stat, sel_lag, diffed), adj_p in zip(_pending, adjusted_ps):
        strength = _evidence_strength(adj_p)
        report.edges.append(GrangerEdge(
            cause=cause,
            effect=effect,
            max_lag=max_lag,
            selected_lag=sel_lag,
            raw_p_value=raw_p,
            adjusted_p_value=float(adj_p),
            f_statistic=f_stat,
            evidence_strength=strength,
            differenced=diffed,
            confounder_candidates=[],
        ))

    # --- B4: Confounder annotation -------------------------------------------
    # Build a lookup: (cause, effect) → edge for significant edges
    sig_set: set[tuple[str, str]] = {
        (e.cause, e.effect) for e in report.edges if e.significant
    }
    for edge in report.edges:
        if not edge.significant:
            continue
        candidates: list[str] = []
        for col in columns:
            if col == edge.cause or col == edge.effect:
                continue
            # Z is a confounder candidate if Z→cause AND Z→effect are both significant
            if (col, edge.cause) in sig_set and (col, edge.effect) in sig_set:
                candidates.append(col)
        edge.confounder_candidates = candidates

    return report
