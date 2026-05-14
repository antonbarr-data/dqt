"""Update the BENCHMARK_STATS block in README.md from examples/benchmarks/results.csv.

Usage:
    uv run python scripts/update_readme_stats.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CSV_PATH = REPO_ROOT / "examples" / "benchmarks" / "results.csv"
README_PATH = REPO_ROOT / "README.md"

START_MARKER = "<!-- BENCHMARK_STATS_START -->"
END_MARKER = "<!-- BENCHMARK_STATS_END -->"


FAMILY_MAP: dict[str, str] = {
    "adwin": "drift", "chi_square_drift": "drift", "js_divergence": "drift",
    "kl_divergence": "drift", "ks_pvalue": "drift", "mmd": "drift",
    "outlier_fraction_drift": "drift", "psi": "drift", "wasserstein_1": "drift",
    "bocpd": "timeseries", "cusum": "timeseries", "holt_winters": "timeseries",
    "matrix_profile": "timeseries", "monotonicity": "timeseries",
    "page_hinkley": "timeseries", "prophet_anomaly": "timeseries",
    "stl_residual_zscore": "timeseries",
    "adjusted_boxplot_fraction": "outlier", "auto_outlier": "outlier",
    "double_mad_outlier_fraction": "outlier", "ecod": "outlier",
    "generalized_esd": "outlier", "grubbs": "outlier", "hbos": "outlier",
    "iqr_fence": "outlier", "isolation_forest_fraction": "outlier",
    "lof": "outlier", "mad_outlier_fraction": "outlier",
    "mahalanobis_distance": "outlier", "one_class_svm": "outlier",
    "zscore_outlier_fraction": "outlier",
    "benford_law_fit": "distribution", "cramers_v": "distribution",
    "mutual_information": "distribution",
}


def _parse_csv(path: Path) -> list[dict]:
    """Return per-detector aggregated rows (avg f1 across datasets)."""
    import csv
    from collections import defaultdict
    by_slug: dict[str, list[float]] = defaultdict(list)
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            slug = row["detector_slug"]
            try:
                by_slug[slug].append(float(row["f1"]))
            except (ValueError, KeyError):
                pass
    rows = []
    for slug, f1_vals in by_slug.items():
        avg_f1 = sum(f1_vals) / len(f1_vals)
        rows.append({"slug": slug, "f1_mean": avg_f1,
                     "family": FAMILY_MAP.get(slug, "rule")})
    return rows


def _safe_float(value) -> float | None:
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def build_stats_line(rows: list[dict]) -> str:
    detectors = [r for r in rows if not r["slug"].startswith("_")]
    n_detectors = len(detectors)
    best_row = max(detectors, key=lambda r: r["f1_mean"])
    best_f1 = best_row["f1_mean"]
    best_slug = best_row["slug"]
    families = {r["family"] for r in detectors}
    n_families = len(families)
    line = (
        f"**{n_detectors} detectors** across {n_families} families"
        f" · best F1 **{best_f1:.3f}** ({best_slug})"
        f" · [full results](examples/benchmarks/results.csv)"
    )
    return line


def update_readme(stats_line: str) -> bool:
    """Replace the content between markers in README.md. Returns True if changed."""
    text = README_PATH.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"{re.escape(START_MARKER)}\n.*?\n{re.escape(END_MARKER)}",
        re.DOTALL,
    )
    replacement = f"{START_MARKER}\n{stats_line}\n{END_MARKER}"
    new_text, count = pattern.subn(replacement, text)
    if count == 0:
        print("ERROR: BENCHMARK_STATS markers not found in README.md", file=sys.stderr)
        sys.exit(1)
    if new_text == text:
        print("README.md benchmark stats already up to date.")
        return False
    README_PATH.write_text(new_text, encoding="utf-8")
    print(f"README.md updated: {stats_line}")
    return True


def main() -> None:
    if not CSV_PATH.exists():
        print(
            f"ERROR: {CSV_PATH} not found. Run benchmarks first:\n"
            "  uv run python benchmarks/run_benchmarks.py",
            file=sys.stderr,
        )
        sys.exit(1)

    detectors = _parse_csv(CSV_PATH)
    if not detectors:
        print("ERROR: no detector rows found in CSV.", file=sys.stderr)
        sys.exit(1)

    stats_line = build_stats_line(detectors)
    update_readme(stats_line)


if __name__ == "__main__":
    main()
