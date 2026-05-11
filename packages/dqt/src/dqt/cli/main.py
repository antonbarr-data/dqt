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


def _resolve_adapter(connection: str):
    """Instantiate the correct WarehouseAdapter from a connection string."""
    if connection.startswith("file://"):
        from dqt.adapters.local import LocalFileAdapter
        return LocalFileAdapter(connection[len("file://"):])
    if connection.startswith("postgresql://") or connection.startswith("postgres://"):
        from dqt.adapters.postgres.adapter import PostgresAdapter
        return PostgresAdapter(connection)
    raise ValueError(
        f"Unsupported connection scheme: '{connection}'. "
        "Supported: file://<path>, postgresql://<...>"
    )


def _results_to_json(results) -> str:
    import json
    return json.dumps({
        "results": [
            {
                "check_id": str(r.check_id),
                "detector_slug": r.detector_slug,
                "verdict": r.verdict.value,
                "score": r.score,
                "plain_english": r.plain_english,
            }
            for r in results
        ]
    }, indent=2)


def _results_to_junit(results) -> str:
    from xml.etree.ElementTree import Element, SubElement, tostring
    suites = Element("testsuites")
    suite = SubElement(suites, "testsuite", name="dqt", tests=str(len(results)))
    for r in results:
        tc = SubElement(suite, "testcase", name=r.detector_slug,
                        classname=str(r.check_id), time="0")
        if r.verdict.value == "fail":
            failure = SubElement(tc, "failure", message=r.plain_english)
            failure.text = r.plain_english
        elif r.verdict.value == "warn":
            SubElement(tc, "system-out").text = r.plain_english
    try:
        from xml.etree.ElementTree import indent as et_indent
        et_indent(suites)
    except (ImportError, TypeError):
        pass
    return '<?xml version="1.0"?>\n' + tostring(suites, encoding="unicode")


def _cmd_run(args: argparse.Namespace) -> None:
    """Load a YAML check file. With --connection, execute checks against the adapter."""
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

    if not getattr(args, "connection", None):
        for check in checks:
            print(
                f"run: {check.detector_slug}  "
                f"[{check.schema_name}.{check.table_name}"
                + (f".{check.column_name}" if check.column_name else "")
                + "]"
            )
        print("\nNote: pass --connection <url> to execute checks.")
        return

    adapter = _resolve_adapter(args.connection)
    from dqt.store.memory import MemoryStore
    from dqt.runner.runner import Runner
    runner = Runner(MemoryStore())

    results = []
    any_fail = False
    for check in checks:
        try:
            result = runner.run(check, adapter)
            results.append(result)
            if result.verdict.value == "fail":
                any_fail = True
        except Exception as exc:
            print(f"error running {check.detector_slug}: {exc}", file=sys.stderr)
            any_fail = True

    output_fmt = getattr(args, "output", "text")
    if output_fmt == "json":
        print(_results_to_json(results))
    elif output_fmt == "junit":
        print(_results_to_junit(results))
    else:
        for r in results:
            print(f"[{r.verdict.value.upper():4s}] {r.detector_slug}: {r.plain_english}")

    sys.exit(1 if any_fail else 0)


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


def _cmd_compile(args: argparse.Namespace) -> None:
    """Compile a dqt YAML check file to the target format."""
    from dqt.checks.loader import load_checks_file, CheckValidationError

    try:
        checks = load_checks_file(args.yaml_file)
    except FileNotFoundError:
        print(f"error: file not found: {args.yaml_file}", file=sys.stderr)
        sys.exit(1)
    except CheckValidationError as exc:
        print(f"error: invalid check YAML: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.to == "dbt":
        from dqt.compat.dbt_tests import checks_to_dbt_yaml
        print(checks_to_dbt_yaml(checks))
    else:
        print(f"error: unknown target '{args.to}'", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(prog="dqt", description="dqt data quality CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # list-detectors
    sub.add_parser("list-detectors", help="List all registered detector slugs by group")

    # run <yaml_file>
    p_run = sub.add_parser("run", help="Run checks; pass --connection to execute against an adapter")
    p_run.add_argument("yaml_file", help="Path to the YAML check file")
    p_run.add_argument("--connection", default=None,
                       help="Connection string, e.g. file:///path/to/data.csv or postgresql://...")
    p_run.add_argument("--output", choices=["text", "json", "junit"], default="text",
                       help="Output format (default: text)")

    # fit <yaml_file>
    p_fit = sub.add_parser("fit", help="Validate a check YAML file and print fit targets")
    p_fit.add_argument("yaml_file", help="Path to the YAML check file")

    # compile <yaml_file> --to dbt
    p_compile = sub.add_parser("compile", help="Compile checks to another format (e.g. dbt)")
    p_compile.add_argument("yaml_file", help="Path to the YAML check file")
    p_compile.add_argument("--to", required=True, choices=["dbt"],
                           help="Target format")

    # demo
    sub.add_parser("demo", help="Run a synthetic in-memory demo with wasserstein_1")

    args = parser.parse_args()

    dispatch = {
        "list-detectors": _cmd_list_detectors,
        "run": _cmd_run,
        "fit": _cmd_fit,
        "compile": _cmd_compile,
        "demo": _cmd_demo,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
