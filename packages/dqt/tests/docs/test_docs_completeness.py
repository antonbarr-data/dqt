"""Structural completeness tests for docs/algorithms/.

Asserts that:
1. Every registered detector slug has a matching docs/algorithms/<slug>.md file.
2. Every docs/algorithms/<slug>.md corresponds to a registered slug (no stale docs).
3. Every detector doc contains the four required sections.

These tests are the verifiable gate that prevents docs from falling behind the registry.
Adding a new detector without a doc file causes test_every_slug_has_a_doc to fail.
Adding a doc without registering the detector causes test_no_stale_docs to fail.
"""
from __future__ import annotations

from pathlib import Path

import pytest

# ── paths ──────────────────────────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[4]
_DOCS_DIR = _REPO_ROOT / "docs" / "algorithms"

# Non-detector markdown files in docs/algorithms/ that should not map to slugs
_EXCLUDE_DOCS = frozenset({
    "README.md",
    "_template.md",
    "detectors.md",
    "checks.md",
    "drift.md",
    "causality.md",
    "timeseries.md",
    "outliers_uni.md",
})

# Sections every detector doc must contain (checked as substrings of the file content)
_REQUIRED_SECTIONS = [
    "## When it works well",
    "## When it fails",          # matches "## When it fails / Limitations" too
    "## Recommended thresholds",
]


def _doc_slugs() -> set[str]:
    return {
        p.stem
        for p in _DOCS_DIR.glob("*.md")
        if p.name not in _EXCLUDE_DOCS
    }


def _registry_slugs() -> set[str]:
    import dqt  # noqa: F401 — triggers registration
    from dqt.algorithms._registry import registry
    return set(registry.slugs())


# ── coverage tests ─────────────────────────────────────────────────────────────

def test_every_slug_has_a_doc() -> None:
    """Every registered detector slug must have docs/algorithms/<slug>.md."""
    missing = _registry_slugs() - _doc_slugs()
    assert not missing, (
        f"{len(missing)} detector(s) have no doc file:\n"
        + "\n".join(f"  - {s}" for s in sorted(missing))
    )


def test_no_stale_docs() -> None:
    """Every docs/algorithms/<slug>.md must correspond to a registered slug."""
    stale = _doc_slugs() - _registry_slugs()
    assert not stale, (
        f"{len(stale)} doc file(s) have no matching registered slug:\n"
        + "\n".join(f"  - {s}" for s in sorted(stale))
    )


# ── section completeness ───────────────────────────────────────────────────────

@pytest.mark.parametrize("slug", sorted(_doc_slugs()))
def test_doc_has_required_sections(slug: str) -> None:
    """Each detector doc must contain all four required structural sections."""
    doc_path = _DOCS_DIR / f"{slug}.md"
    content = doc_path.read_text(encoding="utf-8")
    missing = [s for s in _REQUIRED_SECTIONS if s not in content]
    assert not missing, (
        f"{slug}.md is missing section(s): {missing}\n"
        f"  Path: {doc_path}"
    )
