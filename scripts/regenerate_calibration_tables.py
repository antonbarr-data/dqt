"""Regenerate per-detector calibration tables in docs/algorithms/.

Usage: python scripts/regenerate_calibration_tables.py [--detector SLUG]
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from dqt.algorithms._registry import registry
from dqt.algorithms._calibration import suggest_threshold
import dqt.algorithms.basic, dqt.algorithms.distribution, dqt.algorithms.drift
import dqt.algorithms.info, dqt.algorithms.outliers_multi, dqt.algorithms.outliers_uni
import dqt.algorithms.pattern, dqt.algorithms.referential, dqt.algorithms.schema
import dqt.algorithms.timeseries, dqt.algorithms.custom


def _canonical_fixtures(n: int = 5000, seed: int = 42) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    return {
        "normal":      pd.DataFrame({"value": rng.normal(0, 1, n)}),
        "lognormal":   pd.DataFrame({"value": rng.lognormal(0, 1, n)}),
        "poisson":     pd.DataFrame({"value": rng.poisson(5, n).astype(float)}),
        "beta":        pd.DataFrame({"value": rng.beta(2, 5, n)}),
        "pareto":      pd.DataFrame({"value": (rng.pareto(2, n) + 1) * 10}),
        "exponential": pd.DataFrame({"value": rng.exponential(1, n)}),
    }


def _calibrate_one(slug: str, target_fpr: float = 0.001) -> dict:
    cls = registry.get(slug)
    out = {}
    fixtures = _canonical_fixtures()
    for shape, df in fixtures.items():
        try:
            detector = cls()
            result = suggest_threshold(detector, df, target_fpr=target_fpr, n_bootstrap=100)
            out[shape] = (result["suggested_threshold"], result["actual_fpr"])
        except Exception as exc:
            out[shape] = (None, f"error: {type(exc).__name__}: {exc}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--detector", default=None)
    parser.add_argument("--target-fpr", type=float, default=0.001)
    parser.add_argument("--docs-root", default="docs/algorithms")
    args = parser.parse_args()

    targets = [args.detector] if args.detector else sorted(registry.slugs())
    for slug in targets:
        cls = registry.get(slug)
        results = _calibrate_one(slug, target_fpr=args.target_fpr)
        print(f"\n## {slug} (group: {cls.group})")
        for shape, val in results.items():
            print(f"  {shape}: {val}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
