from __future__ import annotations

from dqt.metrics.models import Metric

try:
    from rapidfuzz import fuzz as _fuzz
    _HAS_RAPIDFUZZ = True
except ImportError:
    _HAS_RAPIDFUZZ = False


class MetricRegistry:
    """In-memory registry of Metric definitions."""

    def __init__(self, metrics: list[Metric] | None = None) -> None:
        self._metrics: dict[str, Metric] = {}
        for m in (metrics or []):
            self._metrics[m.fqn] = m

    def get(self, fqn: str) -> Metric | None:
        return self._metrics.get(fqn)

    def search(self, query: str, limit: int = 20) -> list[Metric]:
        q = query.lower()
        if _HAS_RAPIDFUZZ:
            scored = [
                (m, _fuzz.WRatio(q, m.display_name.lower()))
                for m in self._metrics.values()
            ]
            scored.sort(key=lambda x: x[1], reverse=True)
            return [m for m, score in scored[:limit] if score > 40]
        return [
            m for m in self._metrics.values()
            if q in m.display_name.lower() or q in m.fqn.lower()
        ][:limit]

    def list(
        self,
        *,
        tags: list[str] | None = None,
        owner: str | None = None,
        status: str | None = None,
    ) -> list[Metric]:
        results = list(self._metrics.values())
        if tags:
            tag_set = set(tags)
            results = [m for m in results if tag_set.intersection(m.tags)]
        if owner:
            results = [m for m in results if owner in m.owners]
        return results

    def reload(self, metrics: list[Metric]) -> None:
        self._metrics = {m.fqn: m for m in metrics}
