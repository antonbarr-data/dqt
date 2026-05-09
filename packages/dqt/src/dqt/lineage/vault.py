from __future__ import annotations
import re
from pathlib import Path
from dqt.semantic.models import SemanticManifest, DatasetDescription, ColumnDescription
from dqt.lineage.models import LineageGraph, LineageNode

# Vault layout (Karpathy LLM Wiki pattern):
#   raw/   — semantic layer: atomic source-of-truth docs (datasets, columns)
#   wiki/  — synthesised knowledge: metrics, lineage, causal analyses

_RAW = "raw"
_WIKI = "wiki"


def _safe_name(s: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', '_', s)


def write_vault(
    manifest: SemanticManifest,
    graph: LineageGraph,
    vault_dir: str,
    vault_title: str = "dqt Knowledge Graph",
) -> None:
    """
    Generate an Obsidian vault from a semantic manifest + lineage graph.

    Layout:
      vault_dir/
        .obsidian/app.json
        00 Index.md
        raw/
          datasets/<dataset_id>.md     ← semantic layer (source-of-truth)
          columns/<dataset>/<col>.md
        wiki/
          metrics/<metric_id>.md       ← synthesised knowledge
          lineage/causality.md
    """
    root = Path(vault_dir)
    root.mkdir(parents=True, exist_ok=True)

    obsidian_dir = root / ".obsidian"
    obsidian_dir.mkdir(exist_ok=True)
    (obsidian_dir / "app.json").write_text(
        '{\n  "legacyEditor": false,\n  "livePreview": true\n}\n',
        encoding="utf-8",
    )

    # raw/ — semantic layer
    for ds in manifest.datasets:
        _write_dataset_doc(root, ds, graph)
        col_dir = root / _RAW / "columns" / _safe_name(ds.id)
        col_dir.mkdir(parents=True, exist_ok=True)
        for col in ds.columns:
            _write_column_doc(col_dir, ds, col, graph)

    # wiki/ — synthesised knowledge
    metric_nodes = [n for n in graph.nodes if n.kind == "metric"]
    if metric_nodes:
        (root / _WIKI / "metrics").mkdir(parents=True, exist_ok=True)
        for node in metric_nodes:
            _write_metric_doc(root, node, graph)

    causal_edges = [e for e in graph.edges if e.kind == "causality"]
    if causal_edges:
        (root / _WIKI / "lineage").mkdir(parents=True, exist_ok=True)
        _write_causality_doc(root, causal_edges, graph)

    _write_index(root, manifest, graph, vault_title)


def _frontmatter(data: dict) -> str:
    lines = ["---"]
    for k, v in data.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {item}")
        elif isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, str) and any(c in v for c in ':#{}[]|>&*!,?'):
            lines.append(f"{k}: {v!r}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---\n")
    return "\n".join(lines)


def _write_dataset_doc(root: Path, ds: DatasetDescription, graph: LineageGraph) -> None:
    edges_out = [e for e in graph.edges if e.source == ds.id]
    edges_in = [e for e in graph.edges if e.target == ds.id]

    related_nodes = {e.target for e in edges_out} | {e.source for e in edges_in}
    related_links = "\n".join(f"- [[{_node_link(r)}]]" for r in sorted(related_nodes)) or "_None_"

    col_links = "\n".join(
        f"- [[{_RAW}/columns/{_safe_name(ds.id)}/{_safe_name(c.name)}|{c.name}]] — {c.description[:60]}"
        for c in ds.columns
    )

    fm = _frontmatter({
        "type": "dataset",
        "id": ds.id,
        "domain": ds.domain,
        "owner": ds.owner,
        "freshness_sla_hours": ds.freshness_sla_hours,
        "classification": "internal",
        "tags": [ds.domain] if ds.domain else [],
    })

    sla = f"{ds.freshness_sla_hours}h" if ds.freshness_sla_hours else "not set"
    body = f"""# {ds.id}

{ds.description}

## Metadata

| Field | Value |
|---|---|
| Owner | {ds.owner} |
| Domain | {ds.domain} |
| Freshness SLA | {sla} |
| Columns | {len(ds.columns)} |

## Columns

{col_links}

## Relationships

{related_links}
"""
    ds_dir = root / _RAW / "datasets"
    ds_dir.mkdir(parents=True, exist_ok=True)
    (ds_dir / f"{_safe_name(ds.id)}.md").write_text(fm + body, encoding="utf-8")


def _write_column_doc(
    col_dir: Path,
    ds: DatasetDescription,
    col: ColumnDescription,
    graph: LineageGraph,
) -> None:
    node_id = f"{ds.id}.{col.name}"
    edges_out = [e for e in graph.edges if e.source == node_id]
    edges_in = [e for e in graph.edges if e.target == node_id]

    upstream_links = "\n".join(
        f"- [[{_node_link(e.source)}]] ← {e.kind}"
        + (f" (lag {e.lag_weeks}w)" if e.lag_weeks else "")
        for e in edges_in
    ) or "_No upstream lineage_"

    downstream_links = "\n".join(
        f"- [[{_node_link(e.target)}]] → {e.kind}"
        + (f" (lag {e.lag_weeks}w, r={e.confidence:.2f})" if e.lag_weeks else "")
        for e in edges_out
    ) or "_No downstream lineage_"

    fm = _frontmatter({
        "type": "column",
        "dataset": ds.id,
        "name": col.name,
        "classification": col.classification,
        "pii": col.pii,
        "tags": col.tags,
    })

    pii_label = "Yes ⚠️" if col.pii else "No"
    body = f"""# {col.name}

> Dataset: [[{_RAW}/datasets/{_safe_name(ds.id)}]]

{col.description}

## Metadata

| Field | Value |
|---|---|
| Classification | {col.classification} |
| PII | {pii_label} |
| Unit | {col.unit or '—'} |

## Upstream Lineage

{upstream_links}

## Downstream Lineage

{downstream_links}
"""
    (col_dir / f"{_safe_name(col.name)}.md").write_text(fm + body, encoding="utf-8")


def _node_link(node_id: str) -> str:
    """Convert a node ID to its vault path. Column: raw/columns/ds/col. Dataset: raw/datasets/ds. Metric: wiki/metrics/id."""
    if "." in node_id:
        ds, col = node_id.split(".", 1)
        return f"{_RAW}/columns/{_safe_name(ds)}/{_safe_name(col)}"
    return f"{_RAW}/datasets/{_safe_name(node_id)}"


def _write_metric_doc(root: Path, node: LineageNode, graph: LineageGraph) -> None:
    edges_in = [e for e in graph.edges if e.target == node.id]
    source_links = "\n".join(f"- [[{_node_link(e.source)}]]" for e in edges_in) or "_None_"

    fm = _frontmatter({"type": "metric", "id": node.id, **node.metadata})
    body = f"""# {node.label}

{node.metadata.get('description', '')}

## Derived From

{source_links}
"""
    (root / _WIKI / "metrics" / f"{_safe_name(node.id)}.md").write_text(fm + body, encoding="utf-8")


def _write_causality_doc(root: Path, causal_edges: list, graph: LineageGraph) -> None:
    rows = "\n".join(
        f"| [[{_node_link(e.source)}\\|{e.source}]] "
        f"| [[{_node_link(e.target)}\\|{e.target}]] "
        f"| {e.lag_weeks}w | {e.confidence:.2f} | {e.description} |"
        for e in causal_edges
    )
    body = f"""# Causal Relationships

Directed causal edges discovered by statistical analysis (Granger causality / lag-correlation).

| Source | Target | Lag | Confidence | Description |
|---|---|---|---|---|
{rows}
"""
    (root / _WIKI / "lineage" / "causality.md").write_text(body, encoding="utf-8")


def _write_index(root: Path, manifest: SemanticManifest, graph: LineageGraph, title: str) -> None:
    dataset_links = "\n".join(
        f"- [[{_RAW}/datasets/{_safe_name(ds.id)}|{ds.id}]] — {ds.domain}"
        for ds in manifest.datasets
    )
    metric_nodes = [n for n in graph.nodes if n.kind == "metric"]
    metric_links = (
        "\n".join(f"- [[{_WIKI}/metrics/{_safe_name(n.id)}|{n.label}]]" for n in metric_nodes)
        or "_None defined_"
    )
    has_causality = any(e.kind == "causality" for e in graph.edges)

    body = f"""# {title}

This vault documents data assets, column semantics, and discovered relationships.

## Structure

| Folder | Contents |
|---|---|
| `raw/datasets/` | Source-of-truth dataset descriptions (semantic layer) |
| `raw/columns/` | Per-column atomic notes with metadata and lineage links |
| `wiki/metrics/` | Derived metrics and aggregations |
| `wiki/lineage/` | Discovered causal and lineage relationships |

## Datasets

{dataset_links}

## Metrics

{metric_links}

## Lineage
{"- [[wiki/lineage/causality]] — Causal relationships between datasets" if has_causality else "_None recorded_"}
"""
    (root / "00 Index.md").write_text(body, encoding="utf-8")
