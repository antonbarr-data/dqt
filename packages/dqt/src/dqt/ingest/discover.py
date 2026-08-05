"""Recursive discovery of ingestable units in a repo tree.

Walks every file under a root and classifies it per node (not per repo):
- Google OKF concept: a `.md` file that opens with a YAML frontmatter block (`---`).
- Apache Ossie file: a `.yaml`/`.yml`/`.json` whose top level has a `semantic_model` key.
Everything else is ignored. One repo may contain many of each, in any subfolder.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from dqt.ingest.models import Format

_OSSIE_SUFFIXES = {".yaml", ".yml", ".json"}
_IGNORE_DIRS = {".git", "node_modules", "__pycache__", ".venv"}


@dataclass(frozen=True)
class Unit:
    path: Path
    format: Format


def _is_okf_markdown(path: Path) -> bool:
    if path.suffix.lower() != ".md":
        return False
    try:
        with path.open("r", encoding="utf-8") as fh:
            first = fh.readline().strip()
    except (OSError, UnicodeDecodeError):
        return False
    return first == "---"


def _is_ossie_file(path: Path) -> bool:
    if path.suffix.lower() not in _OSSIE_SUFFIXES:
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    if "semantic_model" not in text:  # cheap pre-filter before parsing
        return False
    try:
        doc = yaml.safe_load(text)  # YAML superset also parses JSON
    except yaml.YAMLError:
        return False
    return isinstance(doc, dict) and "semantic_model" in doc


def discover(root: str | Path) -> list[Unit]:
    """Return every ingestable unit under `root`, sorted by path for determinism."""
    root = Path(root)
    units: list[Unit] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in _IGNORE_DIRS for part in path.parts):
            continue
        if _is_okf_markdown(path):
            units.append(Unit(path=path, format="okf"))
        elif _is_ossie_file(path):
            units.append(Unit(path=path, format="ossie"))
    return units
