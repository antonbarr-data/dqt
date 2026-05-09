from __future__ import annotations
import re
from pathlib import Path
from dqt.semantic.models import SemanticManifest, DatasetDescription, ColumnDescription
from dqt.lineage.models import LineageGraph, LineageNode


def _safe_name(s: str) -> str:
    """Sanitize a string for use as an Obsidian file name."""
    return re.sub(r'[\\/:*?"<>|]', '_', s)


def write_vault(
    manifest: SemanticManifest,
    graph: LineageGraph,
    vault_dir: str,
    vault_title: str = "dqt Knowledge Graph",
) -> None:
    """
    Generate an Obsidian vault from a semantic manifest + lineage graph.
    Creates:
      vault_dir/
        .obsidian/app.json
        00 Index.md
        Datasets/<dataset_id>.md
        Columns/<dataset_id>/<column_name>.md
        Metrics/<metric_id>.md  (for metric-kind nodes in graph)
        Lineage/<edge_kind>.md  (one doc per distinct edge kind)
    """
    root = Path(vault_dir)
    root.mkdir(parents=True, exist_ok=True)

    # Minimal .obsidian config (makes the folder openable in Obsidian)
    obsidian_dir = root / ".obsidian"
    obsidian_dir.mkdir(exist_ok=True)
    (obsidian_dir / "app.json").write_text(
        '{\n  "legacyEditor": false,\n  "livePreview": true\n}\n',
        encoding="utf-8",
    )

    # Generate dataset documents
    (root / "Datasets").mkdir(exist_ok=True)
    for ds in manifest.datasets:
        _write_dataset_doc(root, ds, graph)
        # Generate column documents
        col_dir = root / "Columns" / _safe_name(ds.id)
        col_dir.mkdir(parents=True, exist_ok=True)
        for col in ds.columns:
            _write_column_doc(col_dir, ds, col, graph)

    # Generate metric documents
    metric_nodes = [n for n in graph.nodes if n.kind == "metric"]
    if metric_nodes:
        (root / "Metrics").mkdir(exist_ok=True)
        for node in metric_nodes:
            _write_metric_doc(root, node, graph)

    # Generate causal relationship document
    causal_edges = [e for e in graph.edges if e.kind == "causality"]
    if causal_edges:
        (root / "Lineage").mkdir(exist_ok=True)
        _write_causality_doc(root, causal_edges, graph)

    # Index
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
    related_links = "\n".join(f"- [[{r}]]" for r in sorted(related_nodes)) or "_None_"

    col_links = "\n".join(
        f"- [[Columns/{_safe_name(ds.id)}/{_safe_name(c.name)}|{c.name}]] — {c.description[:60]}"
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
    (root / "Datasets" / f"{_safe_name(ds.id)}.md").write_text(fm + body, encoding="utf-8")


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
        f"- [[{_edge_target_link(e.source)}]] <- {e.kind}"
        + (f" (lag {e.lag_weeks}w)" if e.lag_weeks else "")
        for e in edges_in
    ) or "_No upstream lineage_"

    downstream_links = "\n".join(
        f"- [[{_edge_target_link(e.target)}]] -> {e.kind}"
        + (f" (lag {e.lag_weeks}w, confidence {e.confidence:.2f})" if e.lag_weeks else "")
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

    pii_label = "Yes" if col.pii else "No"
    body = f"""# {col.name}

> Dataset: [[Datasets/{_safe_name(ds.id)}]]

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


def _edge_target_link(node_id: str) -> str:
    """Convert a node ID like 'marketing_campaigns.spend_usd' to an Obsidian link path."""
    if "." in node_id:
        parts = node_id.split(".", 1)
        return f"Columns/{_safe_name(parts[0])}/{_safe_name(parts[1])}"
    return f"Datasets/{_safe_name(node_id)}"


def _write_metric_doc(root: Path, node: LineageNode, graph: LineageGraph) -> None:
    edges_in = [e for e in graph.edges if e.target == node.id]
    source_links = "\n".join(f"- [[{_edge_target_link(e.source)}]]" for e in edges_in) or "_None_"

    fm = _frontmatter({"type": "metric", "id": node.id, **node.metadata})
    body = f"""# {node.label}

{node.metadata.get('description', '')}

## Derived From

{source_links}
"""
    (root / "Metrics" / f"{_safe_name(node.id)}.md").write_text(fm + body, encoding="utf-8")


def _write_causality_doc(root: Path, causal_edges: list, graph: LineageGraph) -> None:
    rows = "\n".join(
        f"| [[{_edge_target_link(e.source)}\\|{e.source}]] "
        f"| [[{_edge_target_link(e.target)}\\|{e.target}]] "
        f"| {e.lag_weeks}w | {e.confidence:.2f} | {e.description} |"
        for e in causal_edges
    )
    body = f"""# Causal Relationships

Directed causal edges discovered by statistical analysis (Granger causality / lag-correlation).

| Source | Target | Lag | Confidence | Description |
|---|---|---|---|---|
{rows}
"""
    (root / "Lineage" / "causality.md").write_text(body, encoding="utf-8")


def _write_index(root: Path, manifest: SemanticManifest, graph: LineageGraph, title: str) -> None:
    dataset_links = "\n".join(
        f"- [[Datasets/{_safe_name(ds.id)}]] — {ds.domain}" for ds in manifest.datasets
    )
    metric_nodes = [n for n in graph.nodes if n.kind == "metric"]
    metric_links = "\n".join(f"- [[Metrics/{_safe_name(n.id)}]]" for n in metric_nodes) or "_None defined_"

    body = f"""# {title}

This vault documents the data assets, column semantics, and lineage relationships in the dqt knowledge graph.

## Datasets

{dataset_links}

## Metrics

{metric_links}

## Lineage

- [[Lineage/causality]] — Causal relationships between datasets
"""
    (root / "00 Index.md").write_text(body, encoding="utf-8")
