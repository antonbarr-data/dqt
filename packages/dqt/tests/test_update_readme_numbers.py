# packages/dqt/tests/test_update_readme_numbers.py
"""Tests for scripts/update_readme_numbers.py."""
import sys
from pathlib import Path

import pytest

# Add scripts/ to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))


def test_build_line_format():
    from update_readme_numbers import _build_line
    line = _build_line(64, 9)
    assert "64 detectors" in line
    assert "9 adapters" in line


def test_update_readme_replaces_block(tmp_path):
    from update_readme_numbers import update_readme, _START, _END
    readme = tmp_path / "README.md"
    readme.write_text(
        f"# dqt\n\n{_START}\nold content\n{_END}\n\nmore text\n",
        encoding="utf-8",
    )
    update_readme(readme)
    content = readme.read_text(encoding="utf-8")
    assert "old content" not in content
    assert "detectors" in content
    assert "adapters" in content
    assert _START in content
    assert _END in content


def test_update_readme_idempotent(tmp_path):
    from update_readme_numbers import update_readme, _START, _END
    readme = tmp_path / "README.md"
    readme.write_text(f"# dqt\n{_START}\nold\n{_END}\n", encoding="utf-8")
    update_readme(readme)
    content_first = readme.read_text(encoding="utf-8")
    update_readme(readme)
    content_second = readme.read_text(encoding="utf-8")
    assert content_first == content_second
