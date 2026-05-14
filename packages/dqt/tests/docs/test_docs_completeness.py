"""
Asserts every detector registered in the dqt registry has a doc page at
docs/algorithms/<group>/<slug>.md with all 9 required sections.
Run: pytest packages/dqt/tests/docs/test_docs_completeness.py
"""
import pathlib

import pytest

# Import all algorithm groups to populate the registry before calling slugs().
import dqt.algorithms.basic  # noqa: F401
import dqt.algorithms.custom  # noqa: F401
import dqt.algorithms.drift  # noqa: F401
import dqt.algorithms.info  # noqa: F401
import dqt.algorithms.outliers_multi  # noqa: F401
import dqt.algorithms.outliers_uni  # noqa: F401
import dqt.algorithms.pattern  # noqa: F401
import dqt.algorithms.referential  # noqa: F401
import dqt.algorithms.schema  # noqa: F401
import dqt.algorithms.timeseries  # noqa: F401
from dqt.algorithms._registry import registry

DOCS_ROOT = pathlib.Path(__file__).parents[4] / "docs" / "algorithms"

REQUIRED_SECTIONS = [
    "## What it computes",
    "## Assumptions",
    "## When it works well",
    "## When it fails",
    "## Default-threshold calibration",
    "## Recommended thresholds per data shape",
    "## Citation",
    "## API example",
    "## Limitations",
]

_SLUGS = sorted(registry.slugs())


def _find_doc(slug: str) -> pathlib.Path | None:
    matches = list(DOCS_ROOT.rglob(f"{slug}.md"))
    subdir = [m for m in matches if m.parent != DOCS_ROOT]
    return subdir[0] if subdir else (matches[0] if matches else None)


@pytest.mark.parametrize("slug", _SLUGS)
def test_doc_exists(slug: str) -> None:
    doc = _find_doc(slug)
    assert doc is not None, (
        f"No doc page for '{slug}' — create docs/algorithms/<group>/{slug}.md"
    )


@pytest.mark.parametrize("slug", _SLUGS)
def test_doc_has_required_sections(slug: str) -> None:
    doc = _find_doc(slug)
    if doc is None:
        pytest.skip(f"Doc for '{slug}' not found (covered by test_doc_exists)")
    content = doc.read_text(encoding="utf-8")
    missing = [s for s in REQUIRED_SECTIONS if s not in content]
    assert not missing, (
        f"Doc for '{slug}' missing sections:\n" + "\n".join(f"  {s}" for s in missing)
    )
