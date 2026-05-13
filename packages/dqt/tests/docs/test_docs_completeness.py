"""Every registered detector must have a doc page at docs/algorithms/<group>/<slug>.md."""
from pathlib import Path
import pytest

from dqt.algorithms._registry import registry
import dqt.algorithms.basic, dqt.algorithms.distribution, dqt.algorithms.drift
import dqt.algorithms.info, dqt.algorithms.outliers_multi, dqt.algorithms.outliers_uni
import dqt.algorithms.pattern, dqt.algorithms.referential, dqt.algorithms.schema
import dqt.algorithms.timeseries, dqt.algorithms.custom

DOCS_ROOT = Path(__file__).parent.parent.parent.parent.parent / "docs" / "algorithms"

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


def test_every_detector_has_doc():
    missing = []
    for slug in sorted(registry.slugs()):
        cls = registry.get(slug)
        path = DOCS_ROOT / cls.group / f"{slug}.md"
        if not path.exists():
            missing.append(f"{cls.group}/{slug}")
    assert not missing, f"Missing doc pages ({len(missing)}): {missing}"


@pytest.mark.parametrize("slug", sorted(registry.slugs()))
def test_doc_has_required_sections(slug):
    cls = registry.get(slug)
    path = DOCS_ROOT / cls.group / f"{slug}.md"
    if not path.exists():
        pytest.skip(f"No doc yet for {slug}")
    content = path.read_text(encoding="utf-8")
    missing_sections = [s for s in REQUIRED_SECTIONS if s not in content]
    assert not missing_sections, f"{slug} missing sections: {missing_sections}"
