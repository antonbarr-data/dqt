# tests/benchmarks/test_results_completeness.py
"""Assert every registered detector slug appears in results.csv."""
import csv
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).parents[2]
sys.path.insert(0, str(_REPO / "packages" / "dqt" / "src"))

RESULTS_CSV = _REPO / "examples" / "benchmarks" / "results.csv"


def registry_slugs() -> list[str]:
    """Get all registered detector slugs by importing all algorithm modules."""
    # Import all algorithm modules to register their detectors
    import dqt.algorithms.basic
    import dqt.algorithms.custom
    import dqt.algorithms.distribution
    import dqt.algorithms.drift
    import dqt.algorithms.info
    import dqt.algorithms.outliers_multi
    import dqt.algorithms.outliers_uni
    import dqt.algorithms.pattern
    import dqt.algorithms.referential
    import dqt.algorithms.schema
    import dqt.algorithms.timeseries

    from dqt.algorithms._registry import registry

    return sorted(registry.slugs())


def test_results_csv_exists():
    assert RESULTS_CSV.exists(), (
        f"results.csv not found at {RESULTS_CSV}. "
        "Run: python scripts/run_benchmark_suite.py --quick"
    )


@pytest.mark.parametrize("slug", registry_slugs())
def test_slug_has_result(slug: str) -> None:
    """Verify that each registered detector slug has at least one row in results.csv."""
    if not RESULTS_CSV.exists():
        pytest.skip(f"results.csv not found at {RESULTS_CSV}")

    # Read the CSV and collect all detector slugs
    with open(RESULTS_CSV, newline="") as f:
        reader = csv.DictReader(f)
        csv_slugs = {row["detector_slug"] for row in reader}

    assert slug in csv_slugs, f"Detector slug '{slug}' not found in results.csv"


def test_all_slugs_covered() -> None:
    """Verify that results.csv covers all registered detector slugs."""
    if not RESULTS_CSV.exists():
        pytest.skip(f"results.csv not found at {RESULTS_CSV}")

    registry_slug_set = set(registry_slugs())

    # Read the CSV and collect all detector slugs
    with open(RESULTS_CSV, newline="") as f:
        reader = csv.DictReader(f)
        csv_slugs = {row["detector_slug"] for row in reader}

    missing = registry_slug_set - csv_slugs
    assert not missing, f"Missing slugs in results.csv: {missing}"
    assert len(csv_slugs) >= len(registry_slug_set)
