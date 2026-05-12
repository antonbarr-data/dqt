# benchmarks/fixtures.py
"""Synthetic benchmark fixtures — clean vs anomalous pairs per data shape.

8 scenarios covering the main failure modes seen in production warehouses:
abrupt shift, log-scale shift, point anomalies, missing data, scale change,
gradual ramp drift, combined corruption, and tail-behaviour change.
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass


@dataclass
class BenchmarkFixture:
    name: str
    reference: pd.DataFrame
    current_clean: pd.DataFrame    # should PASS
    current_anomalous: pd.DataFrame  # should WARN or FAIL


def make_fixtures(rng: np.random.Generator) -> list[BenchmarkFixture]:
    """Generate all fixtures using the supplied RNG (pass different seeds per trial)."""
    n = 2_000
    return [
        # ── 1. Abrupt mean shift (easy) ───────────────────────────────────────
        BenchmarkFixture(
            name="normal_mean_shift",
            reference=pd.DataFrame({"v": rng.normal(50, 10, n)}),
            current_clean=pd.DataFrame({"v": rng.normal(50, 10, n)}),
            current_anomalous=pd.DataFrame({"v": rng.normal(80, 10, n)}),
        ),
        # ── 2. Log-scale shift (moderate) ────────────────────────────────────
        BenchmarkFixture(
            name="lognormal_tail_shift",
            reference=pd.DataFrame({"v": rng.lognormal(5.0, 0.5, n)}),
            current_clean=pd.DataFrame({"v": rng.lognormal(5.0, 0.5, n)}),
            current_anomalous=pd.DataFrame({"v": rng.lognormal(5.5, 0.5, n)}),
        ),
        # ── 3. Point outliers injected at 5 % (moderate) ─────────────────────
        BenchmarkFixture(
            name="outliers_injected_5pct",
            reference=pd.DataFrame({"v": rng.normal(50, 10, n)}),
            current_clean=pd.DataFrame({"v": rng.normal(50, 10, n)}),
            current_anomalous=pd.DataFrame({
                "v": np.concatenate([
                    rng.normal(50, 10, int(n * 0.95)),
                    rng.normal(200, 5, int(n * 0.05)),
                ])
            }),
        ),
        # ── 4. Null injection at 10 % (easy for null-aware detectors) ─────────
        BenchmarkFixture(
            name="nulls_injected_10pct",
            reference=pd.DataFrame({"v": rng.normal(50, 10, n).tolist()}),
            current_clean=pd.DataFrame({"v": rng.normal(50, 10, n).tolist()}),
            current_anomalous=pd.DataFrame({
                "v": [None if i < int(n * 0.10) else x
                      for i, x in enumerate(rng.normal(50, 10, n).tolist())]
            }),
        ),
        # ── 5. Variance explosion — std doubles (moderate) ───────────────────
        BenchmarkFixture(
            name="variance_explosion",
            reference=pd.DataFrame({"v": rng.normal(50, 10, n)}),
            current_clean=pd.DataFrame({"v": rng.normal(50, 10, n)}),
            current_anomalous=pd.DataFrame({"v": rng.normal(50, 20, n)}),
        ),
        # ── 6. Gradual ramp drift — mean drifts +20 over the batch (hard) ────
        # Tests detectors that process order (CUSUM, PH) vs bulk distributionGS.
        BenchmarkFixture(
            name="gradual_drift",
            reference=pd.DataFrame({"v": rng.normal(50, 10, n)}),
            current_clean=pd.DataFrame({"v": rng.normal(50, 10, n)}),
            current_anomalous=pd.DataFrame({
                "v": rng.normal(50, 10, n) + np.linspace(0, 20, n)
            }),
        ),
        # ── 7. Combined — mean shift + 10 % nulls (moderate) ─────────────────
        BenchmarkFixture(
            name="mixed_drift_and_nulls",
            reference=pd.DataFrame({"v": rng.normal(50, 10, n).tolist()}),
            current_clean=pd.DataFrame({"v": rng.normal(50, 10, n).tolist()}),
            current_anomalous=pd.DataFrame({
                "v": [None if i < int(n * 0.10) else x
                      for i, x in enumerate(rng.normal(75, 10, n).tolist())]
            }),
        ),
        # ── 8. Heavy-tail contamination — 20 % from wide-spread component ────
        # Same mean and similar median; detectors must sense the tail change.
        BenchmarkFixture(
            name="heavy_tail_switch",
            reference=pd.DataFrame({"v": rng.normal(50, 10, n)}),
            current_clean=pd.DataFrame({"v": rng.normal(50, 10, n)}),
            current_anomalous=pd.DataFrame({
                "v": np.concatenate([
                    rng.normal(50, 10, int(n * 0.80)),
                    rng.normal(50, 40, int(n * 0.20)),
                ])
            }),
        ),
    ]
