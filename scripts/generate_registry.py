#!/usr/bin/env python3
"""Generate docs/registry.json from the installed dqt package registry.

Run: uv run python scripts/generate_registry.py
Output: docs/registry.json (committed to the repo; fetched by the website at runtime)

GitHub Actions triggers this automatically when packages/dqt/src/dqt/algorithms/** changes.
"""
from __future__ import annotations

import json
from pathlib import Path

import dqt  # noqa: F401 — triggers @registry.register side effects
from dqt.algorithms._base import BaseAggregateDetector
from dqt.algorithms._registry import registry
from dqt.algorithms._scales import STAT_SCALES

def _count_adapters() -> tuple[int, list[str]]:
    """Count adapter subdirectories (each = one warehouse engine)."""
    adapters_root = Path(__file__).parent.parent / "packages" / "dqt" / "src" / "dqt" / "adapters"
    engines = sorted(
        d.name for d in adapters_root.iterdir()
        if d.is_dir() and not d.name.startswith("_")
    )
    return len(engines), engines

_DETECTOR_GROUPS = {"outliers_uni", "outliers_multi", "drift", "timeseries", "info", "pattern", "custom"}
_CHECK_GROUPS = {"basic", "schema", "referential"}

_GROUP_LABELS: dict[str, str] = {
    "outliers_uni": "Univariate Outliers",
    "outliers_multi": "Multivariate Outliers",
    "drift": "Distribution Drift",
    "timeseries": "Time Series Anomalies",
    "info": "Information Theory",
    "pattern": "Pattern Checks",
    "custom": "Extension Points",
    "basic": "Data Quality Basics",
    "schema": "Schema Checks",
    "referential": "Referential Integrity",
}


def main() -> None:
    slugs = sorted(registry.slugs())
    detectors: list[dict] = []
    checks: list[dict] = []

    for slug in slugs:
        cls = registry._map[slug]
        group = getattr(cls, "group", "unknown")
        scale = STAT_SCALES.get(slug)
        entry = {
            "slug": slug,
            "group": group,
            "group_label": _GROUP_LABELS.get(group, group),
            "label": scale.plain_english_label if scale else slug,
            "hint": scale.hint if scale else "",
            "kind": "aggregate" if issubclass(cls, BaseAggregateDetector) else "sample",
        }
        if group in _DETECTOR_GROUPS:
            detectors.append(entry)
        elif group in _CHECK_GROUPS:
            checks.append(entry)
        else:
            # unknown group — include as check
            checks.append(entry)

    n_adapters, adapter_names = _count_adapters()
    output = {
        "version": dqt.__version__,
        "total": len(slugs),
        "n_detectors": len(detectors),
        "n_checks": len(checks),
        "n_adapters": n_adapters,
        "adapters": adapter_names,
        "detectors": detectors,
        "checks": checks,
    }

    out_path = Path(__file__).parent.parent / "docs" / "registry.json"
    out_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {out_path}")
    print(f"  dqt v{dqt.__version__}: {len(detectors)} detectors, {len(checks)} checks ({len(slugs)} total), {n_adapters} adapters ({', '.join(adapter_names)})")


if __name__ == "__main__":
    main()
