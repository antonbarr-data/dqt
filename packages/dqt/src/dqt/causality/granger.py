# packages/dqt/src/dqt/causality/granger.py
# Ref: Granger (1969) Econometrica 37(3) — Investigating Causal Relations by Econometric Models
# Bivariate Granger causality: does X lag-k help predict Y beyond Y's own lags?
# Uses statsmodels grangercausalitytests (F-test, OLS).
from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

_MIN_ROWS = 20


@dataclass
class GrangerEdge:
    """Result of a single X → Y Granger causality test."""
    cause: str
    effect: str
    max_lag: int
    min_p_value: float  # minimum p-value across lags
    best_lag: int       # lag with lowest p-value
    f_statistic: float  # F-stat at best_lag
    significant: bool   # True if min_p_value < significance level


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
                    "min_p_value": e.min_p_value,
                    "best_lag": e.best_lag,
                    "f_statistic": e.f_statistic,
                    "significant": e.significant,
                }
                for e in self.edges
            ],
        }


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
        Maximum lag to test. statsmodels tests lags 1..max_lag.
    significance_level:
        p-value threshold for declaring an edge significant.
    columns:
        Subset of columns to test. Defaults to all numeric columns.

    Returns
    -------
    GrangerReport with one GrangerEdge per ordered pair.

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

    for cause in columns:
        for effect in columns:
            if cause == effect:
                continue
            data = df[[effect, cause]].dropna().to_numpy(dtype=float)
            if len(data) < max_lag * 2 + 1:
                continue
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", FutureWarning)
                    results = grangercausalitytests(data, maxlag=max_lag, verbose=False)
            except Exception:
                continue

            p_values = {lag: res[0]["ssr_ftest"][1] for lag, res in results.items()}
            f_values = {lag: res[0]["ssr_ftest"][0] for lag, res in results.items()}
            best_lag = min(p_values, key=p_values.get)
            min_p = p_values[best_lag]
            f_stat = f_values[best_lag]

            report.edges.append(GrangerEdge(
                cause=cause,
                effect=effect,
                max_lag=max_lag,
                min_p_value=float(min_p),
                best_lag=int(best_lag),
                f_statistic=float(f_stat),
                significant=bool(min_p < significance_level),
            ))

    return report
