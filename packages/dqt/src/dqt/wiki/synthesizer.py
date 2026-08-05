"""Synthesise wiki entries from raw documents using the configured LLM.

DEPRECATED: LLM Wiki AI-synthesis is superseded by Google OKF / Apache Ossie repo
ingestion (`dqt repo add`, dqt.ingest). Prose concepts now come from OKF bundles and
land in the server-side knowledge store (KnowledgeArtifact) instead of being synthesised
here. This module is kept for backward compatibility until cutover.

Provider + keys come from the environment via dqt.llm.get_llm (DQT_LLM_PROVIDER).
See dqt.llm for provider setup (anthropic needs dqt[wiki]; litellm needs dqt[llm]).
"""
from __future__ import annotations

import hashlib
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from dqt.wiki.models import RawDocument, SyncManifest, WikiEntry

_MAX_TOKENS = 2048

_SYSTEM_PROMPT = """\
You are a knowledge curator for a data engineering team.
Given one or more source documents, write a concise structured knowledge article.

Rules:
- Write in markdown.
- Start with a one-sentence summary as a blockquote (> sentence).
- Use second-level headings (##) for: Key Facts, Data Quality Notes, Related Assets.
- Key Facts: bullet list of the most important findings or definitions.
- Data Quality Notes: any anomalies, risks, freshness concerns, or coverage gaps. Omit the section if none are relevant.
- Related Assets: datasets, metrics, columns, or systems mentioned. Omit if none.
- Be concise. Prefer 150–400 words total.
- Do NOT include a title (it will be added automatically).
- Do NOT wrap in code fences.
"""


def _build_user_message(docs: list[RawDocument]) -> str:
    parts: list[str] = []
    for doc in docs:
        parts.append(f"### {doc.path}  (kind: {doc.kind})\n\n{doc.content[:8000]}")
    return "\n\n---\n\n".join(parts)


def _entry_id(paths: list[str]) -> str:
    """Stable ID derived from the set of source paths."""
    key = "|".join(sorted(paths))
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _content_hash(docs: list[RawDocument]) -> str:
    combined = "".join(d.sha256 for d in sorted(docs, key=lambda d: d.path))
    return hashlib.sha256(combined.encode()).hexdigest()


def _title_from_paths(paths: list[str]) -> str:
    if len(paths) == 1:
        return Path(paths[0]).stem.replace("_", " ").replace("-", " ").title()
    # use common prefix or first path stem
    stems = [Path(p).stem for p in paths]
    return stems[0].replace("_", " ").title()


def synthesize_entries(
    docs: list[RawDocument],
    manifest: SyncManifest,
    *,
    model: str | None = None,
    force: bool = False,
    progress: Callable[[str], None] | None = None,
) -> list[WikiEntry]:
    """Synthesise wiki entries for docs that have changed since last sync.

    Groups documents by their top-level folder (one entry per folder) plus
    individual entries for standalone docs not in a subfolder.

    Returns the list of newly generated (or regenerated) WikiEntry objects.
    Changed entries are added to manifest.entries in-place.
    """
    warnings.warn(
        "LLM Wiki AI-synthesis is deprecated; use Google OKF / Apache Ossie ingest "
        "(`dqt repo add`, dqt.ingest) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    from dqt.llm import get_llm

    llm = get_llm()
    if llm is None:
        raise EnvironmentError(
            "No LLM is configured. Set DQT_LLM_PROVIDER and the matching key "
            "(ANTHROPIC_API_KEY, or LITELLM_MODEL + a LiteLLM key) before running dqt wiki sync."
        )

    # Group docs: one wiki entry per top-level subfolder, individual entries for root files
    groups: dict[str, list[RawDocument]] = {}
    for doc in docs:
        parts = Path(doc.path).parts
        group_key = parts[0] if len(parts) > 1 else "__root__"
        groups.setdefault(group_key, []).append(doc)

    entries: list[WikiEntry] = []

    for group_key, group_docs in sorted(groups.items()):
        # Sub-groups: split large folders by second-level prefix (file stem)
        if len(group_docs) > 8:
            subgroups: dict[str, list[RawDocument]] = {}
            for doc in group_docs:
                parts = Path(doc.path).parts
                sub_key = parts[1] if len(parts) > 2 else Path(doc.path).stem
                subgroups.setdefault(sub_key, []).append(doc)
        else:
            subgroups = {group_key: group_docs}

        for sub_key, batch in subgroups.items():
            hash_val = _content_hash(batch)
            entry_id = _entry_id([d.path for d in batch])

            # Skip if unchanged and not forced
            if not force and manifest.entries.get(entry_id) == hash_val:
                continue

            title = _title_from_paths([d.path for d in batch])
            if progress:
                progress(f"synthesising {title!r} ({len(batch)} doc(s))")

            user_msg = _build_user_message(batch)
            body = llm.complete(
                [{"role": "user", "content": user_msg}],
                system=_SYSTEM_PROMPT,
                model=model,
                max_tokens=_MAX_TOKENS,
            )

            entry = WikiEntry(
                id=entry_id,
                title=title,
                kind=batch[0].kind,
                body=body,
                source_paths=[d.path for d in batch],
                content_hash=hash_val,
                generated_at=datetime.now(timezone.utc).isoformat(),
            )
            entries.append(entry)
            manifest.entries[entry_id] = hash_val

    return entries
