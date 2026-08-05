"""LLM-based extraction of a repo tree into one normalized IngestProposal.

Each discovered unit (Google OKF concept or Apache Ossie file) is pre-parsed for
context, then normalized by the configured LLM into schema-constrained JSON, which is
validated against `UnitExtract`. Units are merged/deduped into a single proposal;
invalid LLM output is retried once, then recorded as a conflict and skipped (never
written blindly).
"""
from __future__ import annotations

import json
from pathlib import Path

from dqt.ingest.discover import discover
from dqt.ingest.models import (
    IngestProposal,
    ProposedColumn,
    ProposedDataset,
    Provenance,
    UnitExtract,
)
from dqt.ingest.preparse import preparse
from dqt.llm import LLMProvider, get_llm

_MAX_RETRIES = 2

_SYSTEM = """\
You normalize data-catalog concepts into strict JSON for a data-quality tool.
Input is one file from a semantic repo: either a Google OKF concept (markdown
frontmatter + body) or an Apache Ossie semantic_model file.

Extract ONLY what the file states. Do not invent tables, columns, or metrics.
Return a single JSON object, no prose, no code fences, matching exactly:

{
  "datasets": [
    {
      "schema_name": str,            // from a "db.schema.table" / "schema.table" resource
      "table": str,
      "description": str|null,
      "primary_key": [str],
      "unique_keys": [[str]],
      "columns": [
        {"name": str, "data_type": str|null, "nullable": bool|null,
         "description": str|null, "is_time": bool, "is_metric": bool,
         "primary_key": bool, "unique": bool}
      ],
      "metrics": [
        {"name": str, "expression": str|null,
         "kind": "sum"|"count"|"ratio"|"model",
         "datatype": str|null, "description": str|null,
         "column_name": str|null}   // null = table-level metric
      ]
    }
  ],
  "knowledge": [
    {"title": str, "kind": "playbook"|"runbook"|"policy"|"other", "body": str}
  ]
}

Rules:
- A concept describing a table/dataset -> a datasets[] entry with its columns.
- A metric concept -> a metrics[] entry (column_name=null for table-level).
- Infer metric kind from the expression: SUM(->"sum", COUNT(->"count", a "/" ratio->"ratio", else "model".
- A playbook/runbook/policy or free prose -> a knowledge[] entry (NOT a dataset).
- If a "db.schema.table" has 3 parts, use the last two as schema_name/table.
- Omit unknown fields as null / empty lists. Output valid JSON only."""


def _strip_fences(raw: str) -> str:
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        if s.endswith("```"):
            s = s[: s.rfind("```")]
    return s.strip()


def _extract_unit(llm: LLMProvider, context: dict) -> UnitExtract:
    prompt = "FILE CONTEXT (JSON):\n" + json.dumps(context, indent=2, default=str)
    last_err: Exception | None = None
    for _ in range(_MAX_RETRIES):
        raw = llm.complete([{"role": "user", "content": prompt}], system=_SYSTEM, max_tokens=4096)
        try:
            return UnitExtract.model_validate_json(_strip_fences(raw))
        except Exception as exc:  # invalid JSON or schema mismatch -> retry
            last_err = exc
    raise ValueError(str(last_err))


def _merge_dataset(agg: dict[str, ProposedDataset], incoming: ProposedDataset, conflicts: list[str]) -> None:
    key = incoming.identity
    if key not in agg:
        agg[key] = incoming
        return
    base = agg[key]
    base.description = base.description or incoming.description
    existing_cols = {c.name.lower(): c for c in base.columns}
    for col in incoming.columns:
        prev = existing_cols.get(col.name.lower())
        if prev is None:
            base.columns.append(col)
            existing_cols[col.name.lower()] = col
        elif prev.data_type and col.data_type and prev.data_type != col.data_type:
            conflicts.append(
                f"{key}.{col.name}: type mismatch {prev.data_type!r} vs {col.data_type!r} (kept first)"
            )
    existing_metrics = {m.name.lower() for m in base.metrics}
    for m in incoming.metrics:
        if m.name.lower() not in existing_metrics:
            base.metrics.append(m)
            existing_metrics.add(m.name.lower())
    for pk in incoming.primary_key:
        if pk not in base.primary_key:
            base.primary_key.append(pk)
    for uk in incoming.unique_keys:
        if uk not in base.unique_keys:
            base.unique_keys.append(uk)
    base.provenance.extend(incoming.provenance)


def _apply_metric_flags(ds: ProposedDataset) -> None:
    """Mark a column is_metric when a column-level metric references it."""
    metric_cols = {m.column_name.lower() for m in ds.metrics if m.column_name}
    for col in ds.columns:
        if col.name.lower() in metric_cols:
            col.is_metric = True


def extract(root: str | Path, *, llm: LLMProvider | None = None) -> IngestProposal:
    """Discover, pre-parse, and LLM-extract every unit under `root` into one proposal."""
    root = Path(root)
    llm = llm or get_llm()
    if llm is None:
        raise RuntimeError(
            "Extraction requires an LLM. Configure DQT_LLM_PROVIDER and a key (see dqt.llm)."
        )

    units = discover(root)
    agg: dict[str, ProposedDataset] = {}
    knowledge = []
    conflicts: list[str] = []
    seen: list[str] = []

    for unit in units:
        rel = str(unit.path.relative_to(root))
        seen.append(rel)
        prov = Provenance(format=unit.format, path=rel)
        try:
            result = _extract_unit(llm, preparse(unit))
        except Exception as exc:
            conflicts.append(f"{rel}: extraction failed: {exc}")
            continue
        for ds in result.datasets:
            ds.provenance = [prov]
            _merge_dataset(agg, ds, conflicts)
        for kc in result.knowledge:
            kc.provenance = prov
            knowledge.append(kc)

    for ds in agg.values():  # flag metric columns after cross-unit merge
        _apply_metric_flags(ds)

    return IngestProposal(
        datasets=list(agg.values()),
        knowledge=knowledge,
        conflicts=conflicts,
        sources_seen=seen,
    )
