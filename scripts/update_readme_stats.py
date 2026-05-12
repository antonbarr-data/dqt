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


def _parse_csv(path: Path) -> tuple[list[dict], list[dict]]:
    """Return (detector_rows, baseline_rows) as dicts."""
    import csv
    detectors, baselines = [], []
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["family"] == "baseline":
                baselines.append(row)
            else:
                detectors.append(row)
    return detectors, baselines


def _safe_float(value: str) -> float | None:
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def build_stats_line(detectors: list[dict], baselines: list[dict]) -> str:
    n_detectors = len(detectors)

    # Best single F1 across all non-baseline detectors
    best_row = max(
        detectors,
        key=lambda r: _safe_float(r["f1_mean"]) or 0.0,
    )
    best_f1 = _safe_float(best_row["f1_mean"]) or 0.0
    best_slug = best_row["slug"]
    best_lo = _safe_float(best_row["f1_ci_lo"]) or best_f1
    best_hi = _safe_float(best_row["f1_ci_hi"]) or best_f1
    n_trials = best_row.get("n_trials", "30")

    # Count families
    families = {r["family"] for r in detectors}
    n_families = len(families)

    line = (
        f"**{n_detectors} detectors** across {n_families} families"
        f" · best F1 **{best_f1:.3f}** ({best_slug}, {n_trials}-trial 95% CI"
        f" [{best_lo:.3f}, {best_hi:.3f}])"
        f" · benchmarked on 8 synthetic scenarios"
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

    detectors, baselines = _parse_csv(CSV_PATH)
    if not detectors:
        print("ERROR: no detector rows found in CSV.", file=sys.stderr)
        sys.exit(1)

    stats_line = build_stats_line(detectors, baselines)
    update_readme(stats_line)


if __name__ == "__main__":
    main()
