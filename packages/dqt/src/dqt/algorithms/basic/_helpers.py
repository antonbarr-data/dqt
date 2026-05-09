from __future__ import annotations

import pandas as pd

from dqt.algorithms._base import DetectorResult


def fraction_result(df: pd.DataFrame, slug: str, label: str) -> DetectorResult:
    from dqt.algorithms._base import compute_verdict
    row = df.iloc[0]
    total = int(row["total_count"])
    frac = int(row["violation_count"]) / total if total > 0 else 0.0
    return DetectorResult(
        score=frac,
        verdict=compute_verdict(frac, slug),
        plain_english=f"{frac:.2%} of values violate {label}",
        details={"violation_fraction": frac, "violation_count": int(row["violation_count"]), "total": total},
    )
