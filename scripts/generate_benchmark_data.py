#!/usr/bin/env python3
"""Generate deterministic labeled benchmark fixtures.

Usage:
    python scripts/generate_benchmark_data.py [--out-dir data]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

RNG_SEED = 42


def _inject_anomalies(
    arr: np.ndarray, rng: np.random.Generator, frac: float = 0.01
) -> tuple[np.ndarray, np.ndarray]:
    """Return (arr_with_anomalies, is_anomaly bool array).

    Anomaly value = mean + 10 * std  (extreme enough for all threshold-based detectors).
    """
    n = len(arr)
    n_anom = max(1, int(n * frac))
    idx = rng.choice(n, size=n_anom, replace=False)
    out = arr.copy()
    mu, sigma = arr.mean(), arr.std()
    sigma = sigma if sigma > 0 else 1.0
    sign = rng.choice([-1, 1], size=n_anom)
    out[idx] = mu + sign * 10 * sigma
    labels = np.zeros(n, dtype=int)
    labels[idx] = 1
    return out, labels


def generate_shapes(out_dir: Path) -> None:
    out_dir = out_dir / "data_shapes"
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(RNG_SEED)
    N = 5_000

    specs: list[tuple[str, np.ndarray]] = [
        ("normal", rng.standard_normal(N)),
        ("lognormal", rng.lognormal(mean=0.0, sigma=0.5, size=N)),
        ("poisson", rng.poisson(lam=10, size=N).astype(float)),
        ("beta", rng.beta(a=2, b=5, size=N) * 100),
        ("pareto", (rng.pareto(a=3, size=N) + 1) * 10),
        ("exponential", rng.exponential(scale=2.0, size=N)),
    ]
    for name, raw in specs:
        values, labels = _inject_anomalies(raw, frac=0.01, rng=rng)
        df = pd.DataFrame({"value": values, "is_anomaly": labels})
        path = out_dir / f"{name}_5000.csv"
        df.to_csv(path, index=False)
        print(f"  {path}  ({labels.sum()} anomalies / {N} rows)")


def generate_orders_dirty(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(RNG_SEED + 1)
    N = 50_000
    N_OUTLIERS = 50
    amounts = rng.lognormal(mean=4.0, sigma=0.8, size=N)
    outlier_idx = rng.choice(N, size=N_OUTLIERS, replace=False)
    labels = np.zeros(N, dtype=int)
    labels[outlier_idx] = 1
    amounts[outlier_idx] = amounts.mean() + rng.choice(
        [-1, 1], size=N_OUTLIERS
    ) * (15 * amounts.std())
    df = pd.DataFrame(
        {
            "order_id": [f"O{i:06d}" for i in range(N)],
            "amount": amounts.round(2),
            "quantity": rng.integers(1, 20, size=N),
            "customer_id": [f"C{i:05d}" for i in rng.integers(1, 5000, size=N)],
            "created_at": pd.date_range(
                "2024-01-01", periods=N, freq="2min"
            ).astype(str),
            "is_outlier": labels,
        }
    )
    path = out_dir / "orders_dirty.csv"
    df.to_csv(path, index=False)
    print(f"  {path}  ({N_OUTLIERS} outliers / {N} rows)")


def generate_daily_metrics(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(RNG_SEED + 2)
    N = 180
    CHANGEPOINTS = frozenset({30, 60, 120, 150})
    values = np.zeros(N)
    level = 100.0
    for i in range(N):
        if i in CHANGEPOINTS:
            level += rng.choice([-1, 1]) * rng.uniform(20, 40)
        values[i] = level + rng.normal(0, 3)
    labels = np.zeros(N, dtype=int)
    for cp in CHANGEPOINTS:
        labels[cp] = 1
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=N, freq="D").astype(
                str
            ),
            "value": values.round(4),
            "is_changepoint": labels,
        }
    )
    path = out_dir / "daily_metrics_dirty.csv"
    df.to_csv(path, index=False)
    print(f"  {path}  ({len(CHANGEPOINTS)} changepoints / {N} rows)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="data", type=Path)
    args = parser.parse_args()
    print("Generating benchmark data...")
    generate_shapes(args.out_dir)
    generate_orders_dirty(args.out_dir)
    generate_daily_metrics(args.out_dir)
    print("Done.")


if __name__ == "__main__":
    main()
