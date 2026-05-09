#!/usr/bin/env python3
"""Generate the Gigler Obsidian vault. Run: uv run python examples/gigler/generate_vault.py"""
from __future__ import annotations

import sys
from pathlib import Path

# Repo root on sys.path (so dqt is importable without install)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT / "packages" / "dqt" / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "packages" / "dqt" / "src"))

from dqt.semantic.loader import load_semantic_manifest
from dqt.lineage.models import LineageEdge, LineageGraph, LineageNode
from dqt.lineage.vault import write_vault

_SCRIPT_DIR = Path(__file__).parent


def build_graph(manifest) -> LineageGraph:
    graph = LineageGraph()

    # Dataset nodes
    for ds in manifest.datasets:
        graph.add_node(LineageNode(id=ds.id, kind="dataset", label=ds.id))
        # Column nodes
        for col in ds.columns:
            graph.add_node(LineageNode(
                id=f"{ds.id}.{col.name}",
                kind="column",
                label=col.name,
                dataset=ds.id,
                column=col.name,
            ))

    # Metric nodes
    graph.add_node(LineageNode(
        id="weekly_acquisition_spend",
        kind="metric",
        label="Weekly Acquisition Spend",
        metadata={
            "description": "Total USD spend on acquisition campaigns, aggregated by ISO week.",
            "unit": "USD",
            "domain": "marketing",
        },
    ))
    graph.add_node(LineageNode(
        id="weekly_transaction_volume",
        kind="metric",
        label="Weekly Transaction Volume",
        metadata={
            "description": "Total count of completed transactions on the Gigler platform, aggregated by ISO week.",
            "unit": "count",
            "domain": "platform",
        },
    ))

    # Causal edge: acquisition spend -> transaction volume (2-week lag)
    graph.add_edge(LineageEdge(
        source="marketing_campaigns.spend_usd",
        target="gigler_transactions.amount_usd",
        kind="causality",
        lag_weeks=2,
        confidence=0.60,
        description="Acquisition spend drives transaction volume with 2-week lag (Pearson r=0.603)",
    ))

    # Aggregation edges: columns -> metrics
    graph.add_edge(LineageEdge(
        source="marketing_campaigns.spend_usd",
        target="weekly_acquisition_spend",
        kind="aggregates",
    ))
    graph.add_edge(LineageEdge(
        source="gigler_transactions.amount_usd",
        target="weekly_transaction_volume",
        kind="aggregates",
    ))

    # Derivation edges
    graph.add_edge(LineageEdge(
        source="marketing_campaigns.conversions",
        target="marketing_campaigns.revenue_usd",
        kind="derived_from",
        description="revenue_usd = conversions * avg_price_per_tier (price_range)",
    ))
    graph.add_edge(LineageEdge(
        source="gigler_transactions.amount_usd",
        target="gigler_transactions.platform_fee_usd",
        kind="derived_from",
        description="platform_fee_usd = 0.20 * amount_usd",
    ))

    return graph


def main() -> None:
    semantic_path = str(_SCRIPT_DIR / "semantic.yaml")
    vault_path = str(_SCRIPT_DIR / "vault")

    print("Loading semantic manifest...")
    manifest = load_semantic_manifest(semantic_path)
    print(f"  {len(manifest.datasets)} datasets, "
          f"{sum(len(d.columns) for d in manifest.datasets)} columns")

    print("Building lineage graph...")
    graph = build_graph(manifest)
    print(f"  {len(graph.nodes)} nodes, {len(graph.edges)} edges")

    print("Writing vault...")
    write_vault(manifest, graph, vault_path, "Gigler Knowledge Graph")

    # Count generated files
    vault = Path(vault_path)
    file_count = sum(1 for f in vault.rglob("*") if f.is_file())
    print(f"  Done: {file_count} files written to {vault_path}")


if __name__ == "__main__":
    main()
