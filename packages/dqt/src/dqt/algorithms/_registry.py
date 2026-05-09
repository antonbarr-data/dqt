# Detector registry for slug-based lookup.
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dqt.algorithms._base import BaseDetector


class Registry:
    def __init__(self) -> None:
        self._map: dict[str, type[BaseDetector]] = {}

    def register(self, cls: type[BaseDetector]) -> type[BaseDetector]:
        self._map[cls.slug] = cls
        return cls

    def get(self, slug: str) -> type[BaseDetector]:
        try:
            return self._map[slug]
        except KeyError:
            raise KeyError(f"Detector slug '{slug}' not registered. Import the detector module first.")

    def slugs(self) -> list[str]:
        return list(self._map.keys())


registry = Registry()
