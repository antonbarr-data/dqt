from __future__ import annotations
import yaml
from pathlib import Path
from dqt.semantic.models import SemanticManifest


def load_semantic_manifest(path: str) -> SemanticManifest:
    with open(path) as f:
        raw = yaml.safe_load(f)
    return SemanticManifest.model_validate(raw)
