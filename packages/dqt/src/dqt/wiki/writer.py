"""Write synthesised WikiEntry objects to wiki/ directory as markdown files."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from dqt.wiki.models import SyncManifest, WikiEntry

_MANIFEST_FILE = ".sync_manifest.json"


def _safe_name(s: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", s)


def _frontmatter(data: dict) -> str:
    lines = ["---"]
    for k, v in data.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {item}")
        elif isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        else:
            lines.append(f"{k}: {v!r}")
    lines.append("---\n")
    return "\n".join(lines)


def write_wiki(
    entries: list[WikiEntry],
    wiki_dir: str | Path,
    manifest: SyncManifest,
) -> None:
    """Write entries to wiki_dir and persist the manifest."""
    root = Path(wiki_dir)
    root.mkdir(parents=True, exist_ok=True)

    for entry in entries:
        kind_dir = root / entry.kind
        kind_dir.mkdir(exist_ok=True)

        fm = _frontmatter({
            "id": entry.id,
            "title": entry.title,
            "kind": entry.kind,
            "generated_at": entry.generated_at,
            "sources": entry.source_paths,
        })
        content = f"{fm}# {entry.title}\n\n{entry.body}\n"
        (kind_dir / f"{_safe_name(entry.id)}.md").write_text(content, encoding="utf-8")

    manifest.last_sync = datetime.now(timezone.utc).isoformat()
    (root / _MANIFEST_FILE).write_text(
        json.dumps(manifest.model_dump(), indent=2),
        encoding="utf-8",
    )


def load_manifest(wiki_dir: str | Path, raw_dir: str, vault_dir: str) -> SyncManifest:
    """Load existing manifest or return a fresh one."""
    manifest_path = Path(wiki_dir) / _MANIFEST_FILE
    if manifest_path.exists():
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return SyncManifest.model_validate(data)
    return SyncManifest(vault_dir=vault_dir, raw_dir=raw_dir)


def read_wiki_entries(wiki_dir: str | Path) -> list[WikiEntry]:
    """Read all wiki entries from wiki_dir for report generation."""
    root = Path(wiki_dir)
    entries: list[WikiEntry] = []
    for md_file in sorted(root.rglob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        # Parse frontmatter
        if text.startswith("---"):
            end = text.index("---", 3)
            fm_text = text[3:end].strip()
            body_start = text.index("\n", end + 3) + 1
            body = text[body_start:].strip()
            fm: dict = {}
            for line in fm_text.splitlines():
                if ": " in line and not line.startswith(" "):
                    k, _, v = line.partition(": ")
                    fm[k] = v.strip().strip("'\"")
            if "id" in fm:
                entries.append(WikiEntry(
                    id=fm.get("id", ""),
                    title=fm.get("title", md_file.stem),
                    kind=fm.get("kind", "other"),
                    body=body,
                    source_paths=[],
                    content_hash="",
                    generated_at=fm.get("generated_at", ""),
                ))
    return entries
