"""dqt LLM Wiki — AI-assisted knowledge synthesis from raw data documents.

Reads raw/ source documents (semantic YAML, tickets, code, reports) and
synthesises structured wiki/ entries using Anthropic Claude.

Requires the optional dqt[wiki] extra: anthropic>=0.26
"""
from dqt.wiki.models import RawDocument, SyncManifest, WikiEntry
from dqt.wiki.loader import load_raw_documents
from dqt.wiki.synthesizer import synthesize_entries
from dqt.wiki.writer import write_wiki

__all__ = [
    "RawDocument",
    "WikiEntry",
    "SyncManifest",
    "load_raw_documents",
    "synthesize_entries",
    "write_wiki",
]
