"""Tests for scripts/update_readme_numbers.py."""
import re
import sys
import tempfile
from pathlib import Path

import pytest

_REPO = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO / "scripts"))
sys.path.insert(0, str(_REPO / "packages" / "dqt" / "src"))

from update_readme_numbers import (  # noqa: E402
    _ADAPTERS,
    _build_line,
    _count_adapters,
    update_readme,
)

_START = "<!-- NUMBERS_START -->"
_END = "<!-- NUMBERS_END -->"
_FAKE_README = f"""# dqt
{_START}
**0 detectors · 0 adapters**
{_END}
"""


def test_adapter_list_matches_real_adapters():
    adapter_dirs = [
        p.name for p in (_REPO / "packages" / "dqt" / "src" / "dqt" / "adapters").iterdir()
        if p.is_dir() and not p.name.startswith("_")
    ]
    for name in _ADAPTERS:
        assert name in adapter_dirs, (
            f"Adapter '{name}' is in _ADAPTERS list but "
            f"packages/dqt/src/dqt/adapters/{name}/ doesn't exist. "
            "Remove it from _ADAPTERS or create the adapter."
        )


def test_count_adapters_equals_list_length():
    assert _count_adapters() == len(_ADAPTERS)


def test_build_line_format():
    line = _build_line(64, 6)
    assert "64" in line
    assert "6" in line
    assert "detectors" in line
    assert "adapters" in line


def test_update_readme_writes_correct_numbers():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(_FAKE_README)
        tmp = Path(f.name)
    try:
        update_readme(tmp)
        content = tmp.read_text(encoding="utf-8")
        block = re.search(
            re.escape(_START) + r"(.*?)" + re.escape(_END),
            content,
            re.DOTALL,
        )
        assert block, "NUMBERS_START/END markers missing after update"
        inner = block.group(1)
        assert "detectors" in inner
        assert "adapters" in inner
        n_adapt = int(re.search(r"(\d+) adapters", inner).group(1))
        assert n_adapt == len(_ADAPTERS), f"Expected {len(_ADAPTERS)} adapters, got {n_adapt}"
    finally:
        tmp.unlink()


def test_update_readme_is_idempotent():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(_FAKE_README)
        tmp = Path(f.name)
    try:
        update_readme(tmp)
        content_after_first = tmp.read_text(encoding="utf-8")
        update_readme(tmp)
        content_after_second = tmp.read_text(encoding="utf-8")
        assert content_after_first == content_after_second
    finally:
        tmp.unlink()
