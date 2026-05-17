"""Search API -- fuzzy metric search."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/metrics", tags=["search"])


@router.get("/search")
async def search_metrics(
    q: str = "",
    tags: str = "",
    status: str = "",
    owner: str = "",
    limit: int = 50,
) -> list[dict]:
    from dqt_server.api.v1.insights import _get_registry, _metric_to_dict

    registry = _get_registry()
    all_metrics = registry.list()

    tag_set = {t.strip() for t in tags.split(",") if t.strip()}
    results = []
    for m in all_metrics:
        if q:
            q_lower = q.lower()
            name_lower = m.display_name.lower()
            fqn_lower = m.fqn.lower()
            if q_lower not in name_lower and q_lower not in fqn_lower:
                try:
                    from rapidfuzz import fuzz
                    if fuzz.partial_ratio(q_lower, name_lower) < 60:
                        continue
                except ImportError:
                    continue
        if tag_set and not tag_set.intersection(set(m.tags or [])):
            continue
        if owner and owner.lower() not in " ".join(m.owners or []).lower():
            continue
        if status and m.current_verdict != status:
            continue
        results.append(_metric_to_dict(m))
        if len(results) >= limit:
            break

    return results
