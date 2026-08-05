"""Recursive discovery: per-node OKF/Ossie detection across nested subfolders."""
from __future__ import annotations

from dqt.ingest.discover import discover


def _write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_discover_mixed_tree(tmp_path):
    _write(tmp_path / "okf/tables/orders.md", "---\ntype: BigQuery Table\n---\n# body\n")
    _write(tmp_path / "okf/metrics/rev.md", "---\ntype: Metric\n---\nbody\n")
    _write(tmp_path / "ossie/sales.yaml", "version: 0.2.0\nsemantic_model:\n  - name: m\n")
    # noise that must be ignored:
    _write(tmp_path / "README.md", "no frontmatter here\n")
    _write(tmp_path / "config.yaml", "just: config\nno_model: true\n")
    _write(tmp_path / ".git/HEAD", "ref: x\n")

    units = discover(tmp_path)
    fmts = sorted((u.format, u.path.name) for u in units)
    assert fmts == [("okf", "orders.md"), ("okf", "rev.md"), ("ossie", "sales.yaml")]


def test_json_ossie_detected(tmp_path):
    _write(tmp_path / "m.json", '{"version":"0.2.0","semantic_model":[{"name":"m"}]}')
    units = discover(tmp_path)
    assert len(units) == 1 and units[0].format == "ossie"
