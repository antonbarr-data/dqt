import pytest
from pathlib import Path
from dqt.semantic.loader import load_semantic_manifest
from dqt.lineage.models import LineageGraph, LineageNode, LineageEdge
from dqt.lineage.vault import write_vault

_SEMANTIC_YAML = Path(__file__).resolve().parent.parent.parent.parent / "examples" / "gigler" / "semantic.yaml"


def test_write_vault_creates_expected_files(tmp_path):
    manifest = load_semantic_manifest(str(_SEMANTIC_YAML))
    graph = LineageGraph()
    graph.add_edge(LineageEdge(
        source="marketing_campaigns.spend_usd",
        target="gigler_transactions.amount_usd",
        kind="causality", lag_weeks=2, confidence=0.60,
    ))
    write_vault(manifest, graph, str(tmp_path / "vault"), "Test Vault")
    vault = tmp_path / "vault"
    assert (vault / "00 Index.md").exists()
    assert (vault / "Datasets" / "marketing_campaigns.md").exists()
    assert (vault / "Datasets" / "gigler_transactions.md").exists()
    assert (vault / "Columns" / "marketing_campaigns" / "spend_usd.md").exists()
    assert (vault / "Lineage" / "causality.md").exists()
    # verify wiki-link present in causality doc
    content = (vault / "Lineage" / "causality.md").read_text()
    assert "marketing_campaigns" in content
    assert "gigler_transactions" in content


def test_index_links_all_datasets(tmp_path):
    manifest = load_semantic_manifest(str(_SEMANTIC_YAML))
    graph = LineageGraph()
    write_vault(manifest, graph, str(tmp_path / "vault"))
    index = (tmp_path / "vault" / "00 Index.md").read_text()
    assert "marketing_campaigns" in index
    assert "gigler_transactions" in index
