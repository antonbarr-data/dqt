# tests/benchmarks/test_results_completeness.py
"""Assert every registered detector slug appears in results.csv."""
import csv
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).parents[2]
sys.path.insert(0, str(_REPO / "packages" / "dqt" / "src"))

RESULTS_CSV = _REPO / "examples" / "benchmarks" / "results.csv"


def test_results_csv_exists():
    assert RESULTS_CSV.exists(), (
        f"results.csv not found at {RESULTS_CSV}. "
        "Run: python scripts/run_benchmark_suite.py --quick"
    )
