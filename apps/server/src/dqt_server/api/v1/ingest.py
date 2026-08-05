"""Google OKF / Apache Ossie repo ingestion.

Flow: register a Git repo against an existing Source -> clone + LLM-extract (off the
request path) into a reviewable ImportProposal -> user selects -> apply creates only
the selected datasets/columns/metrics + DISABLED checks, reusing existing write paths.
The proposal is the dry-run: nothing is written until /apply.
"""
from __future__ import annotations

import asyncio
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dqt_server.check_runner import _default_schema_for_source, _make_adapter
from dqt_server.db.engine import AsyncSessionLocal, get_db
from dqt_server.models.core import ColumnCheck, Dataset, Source
from dqt_server.models.ingest import ImportProposal, KnowledgeArtifact, KnowledgeRepo

log = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["ingest"])

_CLONE_TIMEOUT_S = 180


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─── clone + build (sync; run in an executor) ────────────────────────────────

def _clone_repo(git_url: str, branch: str | None, subpath: str | None) -> tuple[Path, str, Path | None]:
    """Return (root_to_ingest, commit_sha, tempdir_to_cleanup). Supports local paths."""
    local = Path(git_url).expanduser()
    if local.exists() and local.is_dir():
        root = local / subpath if subpath else local
        return root, "local", None
    tmp = Path(tempfile.mkdtemp(prefix="dqt-repo-"))
    cmd = ["git", "clone", "--depth", "1"]
    if branch:
        cmd += ["--branch", branch]
    cmd += [git_url, str(tmp)]
    subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=_CLONE_TIMEOUT_S)
    commit = subprocess.run(
        ["git", "-C", str(tmp), "rev-parse", "HEAD"],
        capture_output=True, text=True,
    ).stdout.strip()
    root = tmp / subpath if subpath else tmp
    return root, commit, tmp


def _live_columns(adapter, schema: str, table: str) -> dict | None:
    """Return {name_lower: ColumnMeta} for a live table, or None if it doesn't exist."""
    try:
        cols = adapter.describe_columns(schema, table)
    except Exception:
        return None
    return {c.name.lower(): c for c in cols}


def _build_proposal_sync(source: Source, git_url: str, branch: str | None, subpath: str | None) -> tuple[dict, str]:
    """Clone, extract via LLM, reconcile against the live Source. Returns (payload, commit)."""
    from dqt.ingest import derive_checks, extract

    root, commit, tmp = _clone_repo(git_url, branch, subpath)
    try:
        proposal = extract(root)
        adapter = _make_adapter(source)
        default_schema = _default_schema_for_source(source)

        ds_out: list[dict] = []
        for ds in proposal.datasets:
            schema = ds.schema_name or default_schema or "public"
            live = _live_columns(adapter, schema, ds.table)
            available = live is not None
            cols_out = []
            for c in ds.columns:
                in_src = bool(live) and c.name.lower() in live
                cols_out.append({
                    **c.model_dump(),
                    "available": in_src,
                    "live_data_type": (live[c.name.lower()].data_type if in_src else None),
                })
            metrics_out = [
                {**m.model_dump(), "id": f"{ds.identity}::metric::{m.name}"}
                for m in ds.metrics
            ]
            ds_out.append({
                "id": ds.identity,
                "schema_name": ds.schema_name,
                "table": ds.table,
                "description": ds.description,
                "available": available,
                "primary_key": ds.primary_key,
                "unique_keys": ds.unique_keys,
                "columns": cols_out,
                "metrics": metrics_out,
                "provenance": [p.model_dump() for p in ds.provenance],
            })

        checks_out = [
            {
                "id": f"{c.dataset}::check::{c.column_name or '*'}::{c.detector_slug}",
                "dataset": c.dataset,
                "column_name": c.column_name,
                "detector_slug": c.detector_slug,
                "params": c.params,
                "rationale": c.rationale,
                "enabled": c.enabled,
            }
            for c in derive_checks(proposal.datasets)
        ]
        knowledge_out = [
            {"id": f"kn::{i}", "title": k.title, "kind": k.kind, "body": k.body,
             "provenance": (k.provenance.model_dump() if k.provenance else None)}
            for i, k in enumerate(proposal.knowledge)
        ]
        payload = {
            "datasets": ds_out,
            "checks": checks_out,
            "knowledge": knowledge_out,
            "conflicts": proposal.conflicts,
            "sources_seen": proposal.sources_seen,
        }
        return payload, commit
    finally:
        if tmp is not None:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


async def _run_extraction(proposal_id: str, repo_id: str, source_id: str,
                          git_url: str, branch: str | None, subpath: str | None) -> None:
    """Background: build the proposal, then persist status + payload."""
    async with AsyncSessionLocal() as db:
        source = await db.get(Source, source_id)
    payload: dict = {}
    commit = "local"
    status = "ready"
    error: str | None = None
    try:
        loop = asyncio.get_event_loop()
        payload, commit = await loop.run_in_executor(
            None, _build_proposal_sync, source, git_url, branch, subpath
        )
    except Exception as exc:  # clone/extraction/adapter failure
        status = "failed"
        error = str(exc)
        log.error("ingest_extraction_failed", repo_id=repo_id, error=error)

    async with AsyncSessionLocal() as db:
        prop = await db.get(ImportProposal, proposal_id)
        if prop is not None:
            prop.status = status
            prop.error = error
            prop.payload = payload
            prop.commit = commit
        repo = await db.get(KnowledgeRepo, repo_id)
        if repo is not None:
            repo.status = status
            repo.last_commit = commit
            repo.last_synced_at = _now()
        await db.commit()


# ─── request/response bodies ─────────────────────────────────────────────────

class RepoRegisterBody(BaseModel):
    git_url: str
    branch: str | None = None
    subpath: str | None = None


class ApplySelection(BaseModel):
    dataset_ids: list[str] = []
    metric_ids: list[str] = []
    check_ids: list[str] = []
    knowledge_ids: list[str] = []


# ─── endpoints ───────────────────────────────────────────────────────────────

@router.post("/sources/{source_id}/repos", status_code=201)
async def register_repo(source_id: str, body: RepoRegisterBody, db: AsyncSession = Depends(get_db)) -> dict:
    source = await db.get(Source, source_id)
    if source is None:
        raise HTTPException(404, detail=f"Source '{source_id}' not found")

    repo = KnowledgeRepo(
        id=f"repo-{uuid4().hex[:8]}",
        source_id=source_id,
        git_url=body.git_url,
        branch=body.branch,
        subpath=body.subpath,
        status="pending",
    )
    db.add(repo)
    await db.flush()  # parent row must exist before the proposal FK references it
    proposal = ImportProposal(
        id=f"prop-{uuid4().hex[:8]}",
        repo_id=repo.id,
        source_id=source_id,
        status="pending",
    )
    db.add(proposal)
    await db.commit()

    asyncio.create_task(
        _run_extraction(proposal.id, repo.id, source_id, body.git_url, body.branch, body.subpath)
    )
    return {"repo_id": repo.id, "proposal_id": proposal.id, "status": "pending"}


@router.get("/proposals/{proposal_id}")
async def get_proposal(proposal_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    prop = await db.get(ImportProposal, proposal_id)
    if prop is None:
        raise HTTPException(404, detail=f"Proposal '{proposal_id}' not found")
    return {
        "id": prop.id,
        "repo_id": prop.repo_id,
        "source_id": prop.source_id,
        "status": prop.status,
        "error": prop.error,
        "commit": prop.commit,
        "applied_at": prop.applied_at.isoformat() if prop.applied_at else None,
        "payload": prop.payload,
    }


@router.post("/proposals/{proposal_id}/apply")
async def apply_proposal(
    proposal_id: str,
    selection: ApplySelection,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    prop = await db.get(ImportProposal, proposal_id)
    if prop is None:
        raise HTTPException(404, detail=f"Proposal '{proposal_id}' not found")
    if prop.status != "ready":
        raise HTTPException(409, detail=f"Proposal is '{prop.status}', not ready to apply")

    payload = prop.payload or {}
    datasets = {d["id"]: d for d in payload.get("datasets", [])}
    checks = {c["id"]: c for c in payload.get("checks", [])}
    knowledge = {k["id"]: k for k in payload.get("knowledge", [])}
    now = _now()

    created = {"datasets": 0, "metrics": 0, "checks": 0, "knowledge": 0}
    skipped: list[str] = []

    # 1) datasets (additive; only ones that exist in the live source)
    applied_ds: set[str] = set()
    for dsid in selection.dataset_ids:
        d = datasets.get(dsid)
        if d is None:
            skipped.append(f"dataset {dsid}: not in proposal")
            continue
        if not d.get("available"):
            skipped.append(f"dataset {dsid}: not present in source")
            continue
        if await db.get(Dataset, dsid) is None:
            db.add(Dataset(id=dsid, source_id=prop.source_id,
                           schema_name=d.get("schema_name") or "default",
                           status="unknown", check_count=0, created_at=now))
            created["datasets"] += 1
        applied_ds.add(dsid)
    await db.flush()

    # 2) metrics (reuse the existing batch service)
    metric_items = []
    for d in datasets.values():
        if d["id"] not in applied_ds:
            continue
        for m in d.get("metrics", []):
            if m["id"] in selection.metric_ids:
                metric_items.append(m)
    if metric_items:
        from dqt_server.api.v1.insights import (
            MetricBatchBody,
            MetricBatchItem,
            create_metrics_batch,
        )
        body = MetricBatchBody(metrics=[
            MetricBatchItem(
                display_name=m["name"],
                kind=m.get("kind", "ratio"),
                dataset=m_dataset(m, datasets),
                description=m.get("description") or "",
                source_id=prop.source_id,
                column_name=m.get("column_name"),
            )
            for m in metric_items
        ])
        res = await create_metrics_batch(body, background_tasks, db)
        created["metrics"] = res.get("created", 0)

    # 3) checks (insert DISABLED directly; batch endpoint can't set enabled=False)
    for cid in selection.check_ids:
        c = checks.get(cid)
        if c is None:
            skipped.append(f"check {cid}: not in proposal")
            continue
        if c["dataset"] not in applied_ds:
            skipped.append(f"check {cid}: parent dataset not selected/available")
            continue
        col = c["column_name"] or "*"
        check_id = f"{c['dataset']}.{col}.{c['detector_slug']}"
        if await db.get(ColumnCheck, check_id) is None:
            db.add(ColumnCheck(
                id=check_id, dataset_id=c["dataset"], column_name=col,
                detector_slug=c["detector_slug"], params=c.get("params") or {},
                rationale=c.get("rationale") or "", enabled=False,
                created_at=now, updated_at=now,
            ))
            created["checks"] += 1

    # 4) knowledge (prose lane -> agent knowledge store)
    for kid in selection.knowledge_ids:
        k = knowledge.get(kid)
        if k is None:
            skipped.append(f"knowledge {kid}: not in proposal")
            continue
        db.add(KnowledgeArtifact(
            id=f"kn-{uuid4().hex[:8]}", source_id=prop.source_id, repo_id=prop.repo_id,
            title=k["title"], kind=k.get("kind", "other"), body=k.get("body", ""),
            provenance=k.get("provenance"), created_at=now,
        ))
        created["knowledge"] += 1

    prop.applied_at = now
    await db.commit()
    return {"created": created, "skipped": skipped}


def m_dataset(metric: dict, datasets: dict) -> str:
    """Find the dataset id owning this metric (metric ids are '<dataset>::metric::<name>')."""
    return metric["id"].split("::metric::", 1)[0]


@router.post("/repos/{repo_id}/sync", status_code=202)
async def sync_repo(repo_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    repo = await db.get(KnowledgeRepo, repo_id)
    if repo is None:
        raise HTTPException(404, detail=f"Repo '{repo_id}' not found")
    repo.status = "pending"
    proposal = ImportProposal(
        id=f"prop-{uuid4().hex[:8]}", repo_id=repo.id, source_id=repo.source_id, status="pending",
    )
    db.add(proposal)
    await db.commit()
    asyncio.create_task(
        _run_extraction(proposal.id, repo.id, repo.source_id, repo.git_url, repo.branch, repo.subpath)
    )
    return {"repo_id": repo.id, "proposal_id": proposal.id, "status": "pending"}


async def knowledge_for_source(source_id: str, db: AsyncSession) -> list[dict]:
    """Agent knowledge (OKF prose concepts) attached to a source. Shared by ask enrichment."""
    q = await db.execute(
        select(KnowledgeArtifact).where(KnowledgeArtifact.source_id == source_id)
        .order_by(KnowledgeArtifact.created_at.desc())
    )
    return [
        {"id": a.id, "title": a.title, "kind": a.kind, "body": a.body}
        for a in q.scalars().all()
    ]


@router.get("/sources/{source_id}/knowledge")
async def list_knowledge(source_id: str, db: AsyncSession = Depends(get_db)) -> list[dict]:
    """List agent-knowledge artifacts imported from Google OKF / Apache Ossie repos."""
    return await knowledge_for_source(source_id, db)


@router.get("/sources/{source_id}/repos")
async def list_repos(source_id: str, db: AsyncSession = Depends(get_db)) -> list[dict]:
    q = await db.execute(
        select(KnowledgeRepo).where(KnowledgeRepo.source_id == source_id)
        .order_by(KnowledgeRepo.created_at.desc())
    )
    return [
        {
            "id": r.id, "git_url": r.git_url, "branch": r.branch, "subpath": r.subpath,
            "status": r.status, "last_commit": r.last_commit,
            "last_synced_at": r.last_synced_at.isoformat() if r.last_synced_at else None,
        }
        for r in q.scalars().all()
    ]
