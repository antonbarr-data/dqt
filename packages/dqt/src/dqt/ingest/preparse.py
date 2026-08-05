"""Deterministic pre-parse of a discovered unit into structured context for the LLM.

We do NOT map to the proposal here (that is the LLM's job); we only split each file
into clean, machine-readable parts so the extraction prompt is small and reliable.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from dqt.ingest.discover import Unit


def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Split a `---`-delimited YAML frontmatter block from the markdown body."""
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text
    raw = "\n".join(lines[1:end])
    body = "\n".join(lines[end + 1:]).strip()
    try:
        front = yaml.safe_load(raw) or {}
    except yaml.YAMLError:
        front = {}
    return (front if isinstance(front, dict) else {}), body


def preparse(unit: Unit) -> dict:
    """Return a context dict describing one unit for the extraction prompt.

    OKF  -> {"format","path","frontmatter","body"}
    Ossie-> {"format","path","semantic_model": <parsed dict>}
    """
    path = unit.path
    text = path.read_text(encoding="utf-8")
    if unit.format == "okf":
        front, body = _split_frontmatter(text)
        return {"format": "okf", "path": str(path), "frontmatter": front, "body": body}
    doc = yaml.safe_load(text)
    return {"format": "ossie", "path": str(path), "semantic_model": doc}
