"""dqt wiki sub-commands: sync and status."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

console = Console()

wiki_app = typer.Typer(help="LLM wiki synthesis from raw documents.")


@wiki_app.command("sync")
def sync_command(
    raw_dir: str = typer.Argument(..., help="Path to raw/ source documents folder."),
    wiki_dir: str = typer.Argument(..., help="Path to wiki/ output folder."),
    model: str = typer.Option(
        None,
        "--model",
        "-m",
        help="Override the model (default: the configured LLM's model).",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Re-synthesise all entries even if source is unchanged.",
    ),
) -> None:
    """Synthesise wiki/ entries from raw/ documents using Anthropic Claude.

    Reads all .md, .yaml, .txt, .sql, .py, .html files under RAW_DIR,
    groups them by top-level subfolder, and asks Claude to write a concise
    knowledge article for each group.  Only re-processes groups whose source
    content has changed since the last sync (unless --force).

    Requires ANTHROPIC_API_KEY environment variable.
    """
    from dqt.wiki.loader import load_raw_documents
    from dqt.wiki.synthesizer import synthesize_entries
    from dqt.wiki.writer import load_manifest, write_wiki

    raw_path = Path(raw_dir)
    wiki_path = Path(wiki_dir)

    if not raw_path.exists():
        console.print(f"[red]raw_dir not found:[/red] {raw_dir}")
        raise typer.Exit(1)

    console.print(f"[dim]Loading documents from[/dim] {raw_dir}")
    docs = load_raw_documents(raw_path)
    if not docs:
        console.print("[yellow]No documents found — nothing to sync.[/yellow]")
        raise typer.Exit(0)
    console.print(f"  {len(docs)} document(s) found")

    manifest = load_manifest(wiki_path, raw_dir, str(wiki_path))

    def _progress(msg: str) -> None:
        console.print(f"  [dim]>[/dim] {msg}")

    try:
        entries = synthesize_entries(docs, manifest, model=model, force=force, progress=_progress)
    except (ImportError, EnvironmentError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    if not entries:
        console.print("[green]All entries up to date.[/green]")
        return

    write_wiki(entries, wiki_path, manifest)
    console.print(f"[green]Wrote {len(entries)} wiki entry/entries to[/green] {wiki_dir}")


@wiki_app.command("status")
def status_command(
    raw_dir: str = typer.Argument(..., help="Path to raw/ source documents folder."),
    wiki_dir: str = typer.Argument(..., help="Path to wiki/ output folder."),
) -> None:
    """Show which raw documents are synced and which need re-synthesis."""
    import hashlib
    from dqt.wiki.loader import load_raw_documents
    from dqt.wiki.writer import load_manifest
    from dqt.wiki.synthesizer import _content_hash, _entry_id

    raw_path = Path(raw_dir)
    wiki_path = Path(wiki_dir)

    docs = load_raw_documents(raw_path)
    manifest = load_manifest(wiki_path, raw_dir, str(wiki_path))

    # Group docs the same way synthesizer does
    from pathlib import Path as _Path
    groups: dict[str, list] = {}
    for doc in docs:
        parts = _Path(doc.path).parts
        group_key = parts[0] if len(parts) > 1 else "__root__"
        groups.setdefault(group_key, []).append(doc)

    table = Table(title="Wiki sync status", show_lines=False)
    table.add_column("Group", style="bold")
    table.add_column("Docs")
    table.add_column("Status")
    table.add_column("Last synced")

    for group_key, group_docs in sorted(groups.items()):
        if len(group_docs) > 8:
            subgroups: dict[str, list] = {}
            for doc in group_docs:
                parts = _Path(doc.path).parts
                sub_key = parts[1] if len(parts) > 2 else _Path(doc.path).stem
                subgroups.setdefault(sub_key, []).append(doc)
        else:
            subgroups = {group_key: group_docs}

        for sub_key, batch in subgroups.items():
            entry_id = _entry_id([d.path for d in batch])
            hash_val = _content_hash(batch)
            last_hash = manifest.entries.get(entry_id)
            if last_hash is None:
                status = "[yellow]pending[/yellow]"
                synced = "-"
            elif last_hash == hash_val:
                status = "[green]up to date[/green]"
                synced = manifest.last_sync[:10] if manifest.last_sync else "?"
            else:
                status = "[red]changed[/red]"
                synced = manifest.last_sync[:10] if manifest.last_sync else "?"
            table.add_row(sub_key, str(len(batch)), status, synced)

    console.print(table)
    if manifest.last_sync:
        console.print(f"[dim]Last full sync:[/dim] {manifest.last_sync}")
