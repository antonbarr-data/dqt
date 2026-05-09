from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from dqt.checks.models import BaselineConfig, Check, CheckFilter, CheckScope


class CheckValidationError(ValueError):
    """Raised when a check YAML document fails schema validation."""


def _load_schema() -> dict[str, Any]:
    schema_path = Path(__file__).parent / "schema" / "check.schema.json"
    with schema_path.open() as f:
        return json.load(f)


def _validate_check_dict(raw: dict[str, Any], schema: dict[str, Any]) -> None:
    try:
        jsonschema.validate(instance=raw, schema=schema)
    except jsonschema.ValidationError as exc:
        raise CheckValidationError(str(exc.message)) from exc


def _parse_check(raw: dict[str, Any]) -> Check:
    baseline_raw = raw.get("baseline")
    baseline = BaselineConfig(**baseline_raw) if baseline_raw else None

    scope_raw = raw.get("scope")
    scope = CheckScope(**scope_raw) if scope_raw else None

    filters = [CheckFilter(**f) for f in raw.get("filters", [])]

    return Check(
        schema_name=raw["schema_name"],
        table_name=raw["table_name"],
        column_name=raw.get("column_name"),
        detector_slug=raw["detector_slug"],
        params=raw.get("params") or {},
        baseline=baseline,
        schedule=raw.get("schedule"),
        sample_n=raw.get("sample_n", 100_000),
        sampling_pct=raw.get("sampling_pct"),
        scope=scope,
        filters=filters,
    )


def load_checks_yaml(yaml_str: str) -> list[Check]:
    """Parse and validate a YAML string containing a `checks:` list. Returns Check objects."""
    schema = _load_schema()
    doc = yaml.safe_load(yaml_str)
    if not isinstance(doc, dict) or "checks" not in doc:
        raise CheckValidationError("YAML must have a top-level 'checks' key")
    checks: list[Check] = []
    for raw in doc["checks"]:
        _validate_check_dict(raw, schema)
        checks.append(_parse_check(raw))
    return checks


def load_checks_file(path: str) -> list[Check]:
    """Load checks from a YAML file on disk."""
    with Path(path).open() as f:
        return load_checks_yaml(f.read())
