"""Significance threshold engine.

Per-metric threshold = mean + sigma * std of rolling day-over-day absolute changes.
Reference: https://en.wikipedia.org/wiki/Standard_deviation
"""
from __future__ import annotations

import math

from dqt.store._protocol import MetricRun

_DEFAULT_THRESHOLD = 0.10  # fallback when fewer than 7 runs available


def compute_threshold(runs: list[MetricRun], *, sigma: float = 2.0) -> float:
    """Return the significance threshold as an absolute fraction (e.g. 0.05 = 5%).

    Args:
        runs:  MetricRun list in chronological order (oldest first).
        sigma: Number of standard deviations above the mean. Default 2.0.

    Returns:
        Threshold value >= 0.01.
    """
    if len(runs) < 7:
        return _DEFAULT_THRESHOLD

    changes: list[float] = []
    for i in range(1, len(runs)):
        prev = runs[i - 1].value
        if prev == 0:
            continue
        changes.append(abs((runs[i].value - prev) / abs(prev)))

    if len(changes) < 3:
        return _DEFAULT_THRESHOLD

    n = len(changes)
    mean = sum(changes) / n
    variance = sum((c - mean) ** 2 for c in changes) / (n - 1)
    std = math.sqrt(variance)

    return max(0.01, mean + sigma * std)
