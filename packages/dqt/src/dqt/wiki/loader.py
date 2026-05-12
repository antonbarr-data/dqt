"""Load raw documents from a raw/ directory tree.

Expected layout:
  raw/
    semantic/   ← YAML semantic layer definitions
    tickets/    ← plain-text or markdown incident/ticket docs
    code/       ← SQL, Python, or other code snippets
    reports/    ← HTML or markdown data reports
    <other>/    ← anything else, treated as kind="other"
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from dqt.wiki.models import RawDocument

_TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".txt", ".sql", ".py", ".json", ".html", ".csv"}

_KIND_MAP: dict[str, Literal["semantic", "ticket", "code", "report", "other"]] = {
    "semantic": "semantic",
    "tickets": "ticket",
    "ticket": "ticket",
    "code": "code",
    "reports": "report",
    "report": "report",
}


def _infer_kind(path: Path, raw_dir: Path) -> Literal["semantic", "ticket", "code", "report", "other"]:
    try:
        rel = path.relative_to(raw_dir)
        top = rel.parts[0].lower() if len(rel.parts) > 1 else ""
        return _KIND_MAP.get(top, "other")
    except ValueError:
        return "other"


def load_raw_documents(raw_dir: str | Path) -> list[RawDocument]:
    """Recursively scan raw_dir and return all readable text documents."""
    root = Path(raw_dir)
    if not root.exists():
        return []

    docs: list[RawDocument] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in _TEXT_SUFFIXES:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        sha = hashlib.sha256(content.encode()).hexdigest()
        docs.append(RawDocument(
            path=str(path.relative_to(root)),
            kind=_infer_kind(path, root),
            content=content,
            sha256=sha,
        ))
    return docs
