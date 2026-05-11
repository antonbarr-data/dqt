# packages/dqt/src/dqt/algorithms/timeseries/prophet_anomaly.py
# Ref: Taylor & Letham (2018) Am. Statistician 72(1) — Forecasting at Scale
# Requires optional dqt[forecast] extra: pip install 'dqt[forecast]'
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
    Raises ImportError with install hint if prophet is not installed.
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
        return {"model": model, "n_train": n, "interval_width": self._interval_width}

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
