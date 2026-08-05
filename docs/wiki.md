# LLM Wiki: AI-assisted knowledge synthesis (deprecated)

> **Deprecated.** LLM Wiki AI-synthesis is superseded by importing open semantic
> formats: [Google OKF](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing)
> and [Apache Ossie](https://ossie.apache.org). Instead of synthesising a wiki from
> raw docs, connect a Git repo of Google OKF bundles or Apache Ossie files to a source
> with `dqt repo add <git-url> --source <id>`: dqt extracts datasets, columns, metrics,
> and prose playbooks, you review and select what to import, and the prose lands in the
> agent knowledge store. See the ingest docs. This page is kept as legacy reference.

dqt ships a pipeline that turns a folder of raw source documents into a structured, AI-written knowledge wiki, then renders it as a shareable HTML report.

The pattern is inspired by [Andrej Karpathy's LLM Wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f): `raw/` holds atomic source-of-truth documents you own and edit; `wiki/` holds synthesised knowledge produced by the AI. The two layers are kept separate on purpose.

---

## Quick start

```bash
pip install dqt-cli          # anthropic>=0.26 bundled
export ANTHROPIC_API_KEY=sk-ant-...

# Put your source docs under raw/
mkdir -p raw/semantic raw/tickets raw/code raw/reports

# Synthesise wiki entries
dqt wiki sync raw/ wiki/

# Regenerate HTML report
dqt report --vault wiki/ --out knowledge_report.html
```

---

## raw/ folder layout

Organise source documents by top-level subfolder. dqt groups all files in each subfolder into one wiki entry.

```
raw/
  semantic/    # YAML metric/dataset definitions, dbt semantic_models.yml
  tickets/     # Incident reports, postmortems, JIRA exports (.md, .txt)
  code/        # SQL queries, Python scripts, dbt models
  reports/     # DQ summaries, profiling outputs (.md, .html)
```

**Supported file types:** `.md`, `.yaml`, `.yml`, `.txt`, `.sql`, `.py`, `.json`, `.html`, `.csv`

Any other top-level subfolder name works too (`governance/`, `adr/`, etc.) — it becomes a wiki entry of kind `other`.

---

## dqt wiki sync

```
dqt wiki sync RAW_DIR WIKI_DIR [OPTIONS]
```

Reads all documents under `RAW_DIR`, groups them by top-level subfolder, and asks Anthropic Claude to write a concise knowledge article for each group. Writes output to `WIKI_DIR` as markdown files with YAML frontmatter.

**Cache behaviour:** a `.sync_manifest.json` file inside `WIKI_DIR` records a SHA-256 hash of each group's content. On subsequent runs, only groups whose source files have changed are re-synthesised.

### Options

| Option | Default | Description |
|---|---|---|
| `--model`, `-m` | `claude-opus-4-7` | Anthropic model to use |
| `--force`, `-f` | `false` | Re-synthesise all groups, even if unchanged |

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Success (or nothing to do) |
| `1` | `RAW_DIR` not found, `ANTHROPIC_API_KEY` not set, or API error |

### Environment variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Required. Your Anthropic API key. |

### What each wiki entry looks like

Each synthesised article is a `.md` file with YAML frontmatter. The body follows a consistent structure:

```markdown
---
id: 'a1b2c3d4e5f6g7h8'
title: 'Semantic'
kind: 'semantic'
generated_at: '2026-05-12T10:30:00+00:00'
sources:
  - semantic/datasets.yaml
  - semantic/metrics.yaml
---
# Semantic

> One-sentence summary of the documents.

## Key Facts

- Bullet list of the most important findings or definitions.

## Data Quality Notes

Any anomalies, coverage gaps, or freshness concerns found in the source docs.

## Related Assets

Datasets, metrics, columns, or systems mentioned in the source.
```

---

## dqt wiki status

```
dqt wiki status RAW_DIR WIKI_DIR
```

Shows which source groups are synced and which need re-synthesis. Useful before a long sync run.

```
Wiki sync status
 Group      Docs  Status       Last synced
 semantic      2  up to date   2026-05-12
 tickets       3  changed      2026-05-10
 code          1  pending      -
 reports       2  up to date   2026-05-12
```

---

## dqt report

```
dqt report --vault WIKI_DIR [OPTIONS]
```

Generates a self-contained dark-mode HTML report from all wiki entries in `WIKI_DIR`. The report uses the same visual language as other dqt reports: JetBrains Mono, sharp corners, dqt accent colour.

### Options

| Option | Default | Description |
|---|---|---|
| `--vault`, `-v` | required | Path to the `wiki/` folder |
| `--out`, `-o` | `wiki_report.html` | Output file path |
| `--title`, `-t` | `Wiki Knowledge Report` | Report title in the header |

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Success (or wiki is empty) |
| `1` | `WIKI_DIR` not found |

---

## Python library API

The full pipeline is importable for custom workflows:

```python
from dqt.wiki import (
    load_raw_documents,   # scan raw/ folder
    synthesize_entries,   # call Anthropic API
    write_wiki,           # write wiki/ files
    SyncManifest,
)
from dqt.wiki.writer import load_manifest, read_wiki_entries

# Load raw documents
docs = load_raw_documents("raw/")

# Load or create a manifest (tracks what has been processed)
manifest = load_manifest("wiki/", raw_dir="raw/", vault_dir="wiki/")

# Synthesise only changed groups
entries = synthesize_entries(
    docs,
    manifest,
    model="claude-opus-4-7",  # or any Anthropic model
    force=False,
    progress=print,
)

# Write to wiki/
write_wiki(entries, "wiki/", manifest)

# Read back all entries (e.g. for a custom report)
all_entries = read_wiki_entries("wiki/")
```

`synthesize_entries` requires `ANTHROPIC_API_KEY` in the environment and the `dqtlib[wiki]` extra (`anthropic>=0.26`).

---

## Gigler example

A working example lives at [examples/gigler/raw/](../examples/gigler/raw/):

```
examples/gigler/raw/
  semantic/datasets.yaml          # dataset definitions for all 4 Gigler tables
  tickets/INC-2024-031.md         # transaction volume drop incident
  code/transaction_roi.sql        # marketing ROI bridge query
  reports/Q1_2025_data_quality_summary.md
```

To run it:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
dqt wiki sync examples/gigler/raw/ examples/gigler/wiki/
dqt report --vault examples/gigler/wiki/ \
           --out examples/gigler/reports/wiki_report.html \
           --title "Gigler Knowledge Report"
```

---

## CI/CD integration

The sync command is idempotent and cache-aware. A typical workflow:

```yaml
# .github/workflows/wiki.yml
- name: Sync wiki
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  run: |
    dqt wiki sync docs/raw/ docs/wiki/
    dqt report --vault docs/wiki/ --out docs/wiki_report.html

- name: Commit updated wiki
  run: |
    git add docs/wiki/ docs/wiki_report.html
    git diff --cached --quiet || git commit -m "chore: update wiki"
```

Only groups whose source files changed will trigger API calls, so cost is proportional to actual document churn.
