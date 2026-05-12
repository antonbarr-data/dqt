"""dqt report — generate an HTML knowledge report from a wiki/ folder."""
from __future__ import annotations

import html as _html
import re
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console

console = Console()

_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body {
  background: #0F1117; color: #E8EAF0;
  font-family: Inter, system-ui, sans-serif;
  font-size: 13px; line-height: 1.6;
}
header {
  padding: 20px 40px 16px;
  border-bottom: 1px solid #2A3147;
  display: flex; flex-direction: column; gap: 4px;
}
.brand {
  font-family: 'JetBrains Mono', monospace; font-weight: 300;
  font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase;
  color: #9DD0B0;
}
h1 { font-size: 20px; font-weight: 300; letter-spacing: -0.02em; color: #E8EAF0; }
.meta { font-size: 11px; color: #666E82; font-family: 'JetBrains Mono', monospace; }
main { max-width: 960px; margin: 0 auto; padding: 24px 40px 48px; }
.summary-bar {
  display: flex; gap: 1px; border: 1px solid #2A3147; margin-bottom: 24px;
}
.summary-stat {
  flex: 1; padding: 10px 16px; background: #161B25;
}
.summary-stat .s-label {
  font-size: 10px; text-transform: uppercase; letter-spacing: 0.12em;
  color: #666E82; font-family: 'JetBrains Mono', monospace;
}
.summary-stat .s-value {
  font-size: 28px; font-weight: 300; color: #9DD0B0;
  font-family: 'JetBrains Mono', monospace;
}
.toc { margin-bottom: 28px; }
.toc h2 { font-size: 11px; text-transform: uppercase; letter-spacing: 0.12em; color: #666E82; margin-bottom: 8px; }
.toc ul { list-style: none; }
.toc li { margin: 3px 0; }
.toc a { color: #9DD0B0; text-decoration: none; font-size: 12px; }
.toc a:hover { text-decoration: underline; }
.entry {
  background: #161B25; border: 1px solid #2A3147;
  margin-bottom: 16px; padding: 20px 24px;
}
.entry-header {
  display: flex; justify-content: space-between; align-items: baseline;
  margin-bottom: 14px; border-bottom: 1px solid #2A3147; padding-bottom: 10px;
}
.entry-title { font-size: 15px; font-weight: 500; color: #E8EAF0; }
.entry-kind {
  font-size: 10px; text-transform: uppercase; letter-spacing: 0.12em;
  color: #9DD0B0; font-family: 'JetBrains Mono', monospace;
}
.entry-body blockquote {
  border-left: 3px solid #9DD0B0; padding: 8px 14px;
  background: #1A2E24; color: #A0A8B8; margin-bottom: 12px; font-size: 12px;
}
.entry-body h2 {
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.10em;
  color: #666E82; margin: 14px 0 6px;
}
.entry-body p { margin: 4px 0; color: #A0A8B8; font-size: 12px; }
.entry-body ul { margin: 4px 0 8px 18px; }
.entry-body li { margin: 2px 0; color: #A0A8B8; font-size: 12px; }
.entry-body strong { color: #E8EAF0; }
.entry-body code {
  font-family: 'JetBrains Mono', monospace; font-size: 11px;
  background: #1E2433; padding: 1px 5px; color: #9DD0B0;
}
footer {
  border-top: 1px solid #2A3147; padding: 12px 40px;
  font-size: 11px; color: #666E82; font-family: 'JetBrains Mono', monospace;
}
"""


def _md_to_html(md: str) -> str:
    """Minimal markdown-to-HTML for wiki bodies (no external dep)."""
    escaped = _html.escape(md)

    # blockquote (> line)
    escaped = re.sub(r"^&gt; ?(.+)$", r"<blockquote>\1</blockquote>", escaped, flags=re.MULTILINE)

    # headings
    escaped = re.sub(r"^### (.+)$", r"<h3>\1</h3>", escaped, flags=re.MULTILINE)
    escaped = re.sub(r"^## (.+)$", r"<h2>\1</h2>", escaped, flags=re.MULTILINE)
    escaped = re.sub(r"^# (.+)$", r"<h2>\1</h2>", escaped, flags=re.MULTILINE)

    # bold
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)

    # inline code
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)

    # ul items
    escaped = re.sub(r"^[-*] (.+)$", r"<li>\1</li>", escaped, flags=re.MULTILINE)
    # wrap consecutive <li> blocks in <ul>
    escaped = re.sub(r"((<li>.+?</li>\n?)+)", r"<ul>\1</ul>", escaped, flags=re.DOTALL)

    # paragraphs: blank-line-separated non-tag lines
    lines = escaped.split("\n")
    result: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("<") or stripped == "":
            result.append(line)
        else:
            result.append(f"<p>{stripped}</p>")
    return "\n".join(result)


def _render(entries: list, title: str, generated_at: str) -> str:
    by_kind: dict[str, int] = {}
    for e in entries:
        by_kind[e.kind] = by_kind.get(e.kind, 0) + 1

    summary_stats = "".join(
        f'<div class="summary-stat">'
        f'<div class="s-label">{k}</div>'
        f'<div class="s-value">{v}</div>'
        f"</div>"
        for k, v in sorted(by_kind.items())
    )
    summary_total = (
        f'<div class="summary-stat">'
        f'<div class="s-label">total entries</div>'
        f'<div class="s-value">{len(entries)}</div>'
        f"</div>"
    )

    toc_items = "".join(
        f'<li><a href="#entry-{e.id}">{_html.escape(e.title)}</a></li>'
        for e in entries
    )

    entry_html_parts: list[str] = []
    for e in entries:
        body_html = _md_to_html(e.body)
        sources_html = ", ".join(
            f"<code>{_html.escape(p)}</code>" for p in e.source_paths
        ) if e.source_paths else ""
        sources_line = f'<p class="meta" style="margin-top:10px">Sources: {sources_html}</p>' if sources_html else ""
        entry_html_parts.append(
            f'<div class="entry" id="entry-{e.id}">'
            f'<div class="entry-header">'
            f'<span class="entry-title">{_html.escape(e.title)}</span>'
            f'<span class="entry-kind">{_html.escape(e.kind)}</span>'
            f"</div>"
            f'<div class="entry-body">{body_html}</div>'
            f"{sources_line}"
            f"</div>"
        )

    entries_html = "\n".join(entry_html_parts)

    return f"""<!DOCTYPE html>
<html data-theme="dark">
<head>
  <meta charset="utf-8">
  <title>{_html.escape(title)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@300;400;500&family=JetBrains+Mono:wght@300;400&display=swap" rel="stylesheet">
  <style>{_CSS}</style>
</head>
<body>
<header>
  <div class="brand">dqt</div>
  <h1>{_html.escape(title)}</h1>
  <div class="meta">generated {generated_at}</div>
</header>
<main>
  <div class="summary-bar">{summary_total}{summary_stats}</div>
  <div class="toc">
    <h2>Contents</h2>
    <ul>{toc_items}</ul>
  </div>
  {entries_html}
</main>
<footer>dqt wiki report &middot; {generated_at}</footer>
</body>
</html>"""


def report_command(
    vault: str = typer.Option(..., "--vault", "-v", help="Path to wiki/ folder."),
    out: str = typer.Option("wiki_report.html", "--out", "-o", help="Output HTML file path."),
    title: str = typer.Option("Wiki Knowledge Report", "--title", "-t", help="Report title."),
) -> None:
    """Generate an HTML knowledge report from a wiki/ folder."""
    from dqt.wiki.writer import read_wiki_entries

    wiki_path = Path(vault)
    if not wiki_path.exists():
        console.print(f"[red]wiki dir not found:[/red] {vault}")
        raise typer.Exit(1)

    entries = read_wiki_entries(wiki_path)
    if not entries:
        console.print("[yellow]No wiki entries found — run 'dqt wiki sync' first.[/yellow]")
        raise typer.Exit(0)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = _render(entries, title, generated_at)

    out_path = Path(out)
    out_path.write_text(html, encoding="utf-8")
    console.print(f"[green]Report written to[/green] {out_path} ({len(entries)} entries)")
