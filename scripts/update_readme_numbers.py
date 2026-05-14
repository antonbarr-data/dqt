#!/usr/bin/env python3
"""Update the NUMBERS_START...NUMBERS_END block in README.md.

Reads detector count from the registry and adapter count from the static list.
Called from Makefile before tagging a release.

Usage:
    python scripts/update_readme_numbers.py [--readme README.md]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


_START = "<!-- NUMBERS_START -->"
_END = "<!-- NUMBERS_END -->"

_ADAPTERS = [
    "postgres", "clickhouse", "bigquery", "snowflake", "databricks", "local",
]


def _count_detectors() -> int:
    sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "dqt" / "src"))
    import dqt  # noqa: F401 — triggers registry side effects
    from dqt.algorithms._registry import registry
    return len(registry.slugs())


def _count_adapters() -> int:
    return len(_ADAPTERS)


def _build_line(n_detectors: int, n_adapters: int) -> str:
    return f"**{n_detectors} detectors · {n_adapters} adapters**"


def update_readme(readme_path: Path) -> None:
    text = readme_path.read_text(encoding="utf-8")
    n_det = _count_detectors()
    n_adapt = _count_adapters()
    new_block = f"{_START}\n{_build_line(n_det, n_adapt)}\n{_END}"
    updated = re.sub(
        re.escape(_START) + r".*?" + re.escape(_END),
        new_block,
        text,
        flags=re.DOTALL,
    )
    if updated == text:
        print("README already up to date.")
        return
    readme_path.write_text(updated, encoding="utf-8")
    print(f"Updated README: {n_det} detectors, {n_adapt} adapters")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readme", default="README.md")
    args = parser.parse_args()
    update_readme(Path(args.readme))


if __name__ == "__main__":
    main()
