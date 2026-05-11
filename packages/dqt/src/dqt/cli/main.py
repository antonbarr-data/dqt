"""dqt data quality CLI — argparse, zero new dependencies."""
from __future__ import annotations

import argparse
import sys


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _import_all_algorithm_modules() -> None:
    """Import every algorithm sub-package so detectors self-register via @registry.register."""
    import dqt.algorithms.basic  # noqa: F401
    import dqt.algorithms.distribution  # noqa: F401
    import dqt.algorithms.drift  # noqa: F401
    import dqt.algorithms.info  # noqa: F401
    import dqt.algorithms.outliers_multi  # noqa: F401
    import dqt.algorithms.outliers_uni  # noqa: F401
    import dqt.algorithms.pattern  # noqa: F401
    import dqt.algorithms.referential  # noqa: F401
    import dqt.algorithms.schema  # noqa: F401
    import dqt.algorithms.timeseries  # noqa: F401
    import dqt.algorithms.custom  # noqa: F401


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def _cmd_list_detectors(_args: argparse.Namespace) -> None:
    """Print all registered detector slugs grouped by group name."""
    _import_all_algorithm_modules()
    from dqt.algorithms._registry import registry

    # Build group → [slug, ...] mapping
    groups: dict[str, list[str]] = {}
    for slug, cls in registry._map.items():
        g = getattr(cls, "group", "ungrouped")
        groups.setdefault(g, []).append(slug)

    for group_name in sorted(groups):
        print(f"\n[{group_name}]")
        for slug in sorted(groups[group_name]):
            print(f"  {slug}")


def _cmd_run(args: argparse.Namespace) -> None:
    """Load a YAML check file and print what would run (adapter required to execute)."""
    from dqt.checks.loader import load_checks_file, CheckValidationError

    try:
        checks = load_checks_file(args.yaml_file)
    except FileNotFoundError:
        print(f"error: file not found: {args.yaml_file}", file=sys.stderr)
        sys.exit(1)
    except CheckValidationError as exc:
        print(f"error: invalid check YAML: {exc}", file=sys.stderr)
        sys.exit(1)

    if not checks:
        print("No checks defined in file.")
        return

    for check in checks:
        print(
            f"run: {check.detector_slug}  "
            f"[{check.schema_name}.{check.table_name}"
            + (f".{check.column_name}" if check.column_name else "")
            + "]"
        )

    print(
        "\nNote: adapter required to run — use the Python API with a WarehouseAdapter."
    )


def _cmd_fit(args: argparse.Namespace) -> None:
    """Load a YAML check file and print fit targets (adapter required to execute)."""
    from dqt.checks.loader import load_checks_file, CheckValidationError

    try:
        checks = load_checks_file(args.yaml_file)
    except FileNotFoundError:
        print(f"error: file not found: {args.yaml_file}", file=sys.stderr)
        sys.exit(1)
    except CheckValidationError as exc:
        print(f"error: invalid check YAML: {exc}", file=sys.stderr)
        sys.exit(1)

    if not checks:
        print("No checks defined in file.")
        return

    for check in checks:
        print(f"fit: {check.id}")

    print(
        "\nNote: adapter required to fit — use the Python API with a WarehouseAdapter."
    )


def _cmd_demo(_args: argparse.Namespace) -> None:
    """Generate a synthetic demo: 30% level shift in 'revenue', run wasserstein_1, print result."""
    import numpy as np
    import pandas as pd

    from dqt.algorithms.drift.wasserstein import Wasserstein1Detector

    rng = np.random.default_rng(42)

    # 90 rows of stable reference data, then 30 rows with a 30% level shift
    base = rng.normal(loc=100.0, scale=10.0, size=90)
    shifted = rng.normal(loc=130.0, scale=10.0, size=30)  # +30% level shift

    reference = pd.DataFrame({"revenue": base})
    current = pd.DataFrame({"revenue": shifted})

    detector = Wasserstein1Detector()
    state = detector.fit(reference)
    result = detector.score(current, state)

    # Use sys.stdout.buffer for byte-safe output on Windows consoles
    def _print(s: str) -> None:
        sys.stdout.buffer.write((s + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()

    _print("=== dqt demo: wasserstein_1 on synthetic 'revenue' column ===")
    _print(f"Reference rows : {len(reference)}")
    _print(f"Current rows   : {len(current)}  (30% level shift at row 90)")
    _print(f"Score          : {result.score:.4f}")
    _print(f"Verdict        : {result.verdict.value}")
    _print(f"Summary        : {result.plain_english}")
    _print(f"Details        : {result.details}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(prog="dqt", description="dqt data quality CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # list-detectors
    sub.add_parser("list-detectors", help="List all registered detector slugs by group")

    # run <yaml_file>
    p_run = sub.add_parser("run", help="Validate a check YAML file and print what would run")
    p_run.add_argument("yaml_file", help="Path to the YAML check file")

    # fit <yaml_file>
    p_fit = sub.add_parser("fit", help="Validate a check YAML file and print fit targets")
    p_fit.add_argument("yaml_file", help="Path to the YAML check file")

    # demo
    sub.add_parser("demo", help="Run a synthetic in-memory demo with wasserstein_1")

    args = parser.parse_args()

    dispatch = {
        "list-detectors": _cmd_list_detectors,
        "run": _cmd_run,
        "fit": _cmd_fit,
        "demo": _cmd_demo,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
