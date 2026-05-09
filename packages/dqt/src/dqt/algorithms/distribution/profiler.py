# Distribution characterization for automatic detector selection.
# Refs:
#   Shapiro & Wilk (1965) Biometrika; D'Agostino & Pearson (1973)
#   Brys, Hubert, Struyf (2004) JRSS-B — medcouple
#   Sarle (1990) — bimodality coefficient
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np
from scipy import stats


class DistributionType(str, Enum):
    NORMAL = "normal"
    SKEWED_POSITIVE = "skewed_positive"
    SKEWED_NEGATIVE = "skewed_negative"
    HEAVY_TAILED = "heavy_tailed"
    MULTIMODAL = "multimodal"
    UNIFORM = "uniform"
    UNKNOWN = "unknown"


@dataclass
class DistributionProfile:
    distribution_type: DistributionType
    skewness: float
    excess_kurtosis: float
    medcouple: float
    is_normal: bool
    is_uniform: bool
    is_multimodal: bool
    sample_size: int


def _bimodality_coefficient(values: np.ndarray) -> float:
    """Sarle's bimodality coefficient. BC > 0.555 ≈ bimodal."""
    n = len(values)
    if n < 4:
        return 0.0
    g1 = float(stats.skew(values))
    g2 = float(stats.kurtosis(values))
    correction = 3.0 * (n - 1) ** 2 / ((n - 2) * (n - 3)) if n > 3 else 3.0
    return (g1 ** 2 + 1.0) / (g2 + correction)


def _medcouple(values: np.ndarray) -> float:
    """Robust skewness measure. Delegates to statsmodels; falls back to sign(skew)/10."""
    try:
        from statsmodels.stats.stattools import medcouple_1d
        return float(medcouple_1d(values))
    except Exception:
        return float(np.sign(stats.skew(values)) * 0.1)


def classify_distribution(values: np.ndarray) -> DistributionProfile:
    """
    Characterise a 1-D numeric array and return a DistributionProfile.
    Uses D'Agostino-Pearson omnibus test for normality (n >= 20),
    Shapiro-Wilk for n < 20, KS-uniform for uniformity,
    and Sarle's bimodality coefficient for multimodality detection.
    """
    values = values[~np.isnan(values)]
    n = len(values)

    skewness = float(stats.skew(values)) if n >= 3 else 0.0
    excess_kurtosis = float(stats.kurtosis(values)) if n >= 4 else 0.0

    if n >= 20:
        _, norm_p = stats.normaltest(values)
    elif n >= 8:
        _, norm_p = stats.shapiro(values)
    else:
        norm_p = 0.0
    is_normal = bool(norm_p > 0.05)

    v_min, v_max = float(values.min()) if n > 0 else 0.0, float(values.max()) if n > 0 else 0.0
    if v_max > v_min and n >= 8:
        normalised = (values - v_min) / (v_max - v_min)
        _, unif_p = stats.kstest(normalised, "uniform")
        is_uniform = bool(unif_p > 0.10)
    else:
        is_uniform = n > 1 and v_max == v_min

    bc = _bimodality_coefficient(values)
    is_multimodal = bc > 0.555

    mc = _medcouple(values) if n >= 10 else 0.0

    dist_type = _classify(is_normal, is_uniform, is_multimodal, skewness, excess_kurtosis, mc)

    return DistributionProfile(
        distribution_type=dist_type,
        skewness=skewness,
        excess_kurtosis=excess_kurtosis,
        medcouple=mc,
        is_normal=is_normal,
        is_uniform=is_uniform,
        is_multimodal=is_multimodal,
        sample_size=n,
    )


def _classify(
    is_normal: bool,
    is_uniform: bool,
    is_multimodal: bool,
    skewness: float,
    excess_kurtosis: float,
    medcouple: float,
) -> DistributionType:
    if is_uniform:
        return DistributionType.UNIFORM
    # Sarle's BC can over-fire on heavily skewed unimodal distributions (lognormal, chi-sq).
    # Only classify as multimodal when skewness is moderate and kurtosis not extreme.
    if is_multimodal and abs(skewness) < 2.0 and excess_kurtosis < 10.0:
        return DistributionType.MULTIMODAL
    if is_normal:
        return DistributionType.NORMAL
    if excess_kurtosis > 3.0 and abs(skewness) <= 0.5:
        return DistributionType.HEAVY_TAILED
    if skewness > 0.5:
        return DistributionType.SKEWED_POSITIVE
    if skewness < -0.5:
        return DistributionType.SKEWED_NEGATIVE
    return DistributionType.UNKNOWN
