# benchmarks/fixtures.py
"""Synthetic benchmark fixtures — clean vs anomalous pairs per data shape."""
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
    n = 500
    return [
        BenchmarkFixture(
            name="normal_mean_shift",
            reference=pd.DataFrame({"v": rng.normal(50, 10, n)}),
            current_clean=pd.DataFrame({"v": rng.normal(50, 10, n)}),
            current_anomalous=pd.DataFrame({"v": rng.normal(80, 10, n)}),
        ),
        BenchmarkFixture(
            name="lognormal_tail_shift",
            reference=pd.DataFrame({"v": rng.lognormal(5.0, 0.5, n)}),
            current_clean=pd.DataFrame({"v": rng.lognormal(5.0, 0.5, n)}),
            current_anomalous=pd.DataFrame({"v": rng.lognormal(5.5, 0.5, n)}),
        ),
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
        BenchmarkFixture(
            name="nulls_injected_10pct",
            reference=pd.DataFrame({"v": rng.normal(50, 10, n).tolist()}),
            current_clean=pd.DataFrame({"v": rng.normal(50, 10, n).tolist()}),
            current_anomalous=pd.DataFrame({
                "v": [None if i < int(n * 0.10) else x
                      for i, x in enumerate(rng.normal(50, 10, n).tolist())]
            }),
        ),
    ]
