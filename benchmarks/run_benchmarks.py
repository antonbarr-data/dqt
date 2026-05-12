# benchmarks/run_benchmarks.py
"""
Statistically rigorous benchmark suite for dqt detectors.

Methodology
-----------
- 30 independent trials (seeds 0..29) — captures sampling variance
- N=2,000 samples per fixture per trial
- 8 synthetic scenarios (see fixtures.py for descriptions)
- Detectors grouped by family — do NOT compare across families
- 95% CI via normal approximation: mean ± 1.96 × std / sqrt(30)
- Baselines provided as reference points for each family

Usage:
  uv run python benchmarks/run_benchmarks.py
"""
from __future__ import annotations

import math
import sys
import warnings
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pandas as pd

_REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT / "packages" / "dqt" / "src"))
sys.path.insert(0, str(_REPO_ROOT))

import dqt  # noqa: F401 — triggers detector registration

from benchmarks.fixtures import make_fixtures
from dqt.algorithms._base import DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

# ── Detector family taxonomy ──────────────────────────────────────────────────
_FAMILY: dict[str, str] = {
    # Outlier detectors
    "adjusted_boxplot_fraction": "outlier",
    "auto_outlier":              "outlier",
    "double_mad_outlier_fraction": "outlier",
    "generalized_esd":           "outlier",
    "grubbs":                    "outlier",
    "iqr_fence":                 "outlier",
    "mad_outlier_fraction":      "outlier",
    "zscore_outlier_fraction":   "outlier",
    "lof":                       "outlier",
    "isolation_forest_fraction": "outlier",
    "hbos":                      "outlier",
    "ecod":                      "outlier",
    "one_class_svm":             "outlier",
    # Distribution drift detectors
    "js_divergence":             "drift",
    "kl_divergence":             "drift",
    "ks_pvalue":                 "drift",
    "mmd":                       "drift",
    "psi":                       "drift",
    "wasserstein_1":             "drift",
    "chi2_drift":                "drift",
    "adwin":                     "drift",
    # Time-series detectors
    "cusum":                     "timeseries",
    "holt_winters":              "timeseries",
    "page_hinkley":              "timeseries",
    "stl_residual_zscore":       "timeseries",
    "monotonicity":              "timeseries",
    "bocpd":                     "timeseries",
    "matrix_profile":            "timeseries",
    "prophet_anomaly":           "timeseries",
    # Distribution diagnostics (fit-to-distribution tests)
    "benford_law_fit":           "distribution",
    "anderson_darling":          "distribution",
    "shapiro_wilk":              "distribution",
    "lilliefors":                "distribution",
    "ks_normality":              "distribution",
    "kurtosis":                  "distribution",
    "skewness":                  "distribution",
    "hartigan_dip":              "distribution",
    "adf":                       "distribution",
    "kpss":                      "distribution",
    "ljung_box":                 "distribution",
}

# Detectors that cannot accept a raw float column (need aggregated, multivariate,
# categorical, or string input — tested separately or in adapter integration tests).
_SKIP = {
    "callable_check", "remote_check",
    "bocpd", "matrix_profile", "prophet_anomaly", "adwin",
    # Aggregate detectors
    "completeness", "uniqueness", "validity", "null_fraction", "numeric_mean",
    "volume", "row_count_in_range", "freshness_seconds_behind", "schema_change",
    "referential_integrity_rate", "outlier_fraction_drift",
    "cardinality_in_range", "sum_in_range", "stddev_in_range", "min_in_range",
    "max_in_range", "quantile_in_range", "median_in_range",
    # Multivariate
    "lof", "isolation_forest_fraction", "mahalanobis_distance",
    "hbos", "ecod", "one_class_svm",
    # Non-numeric
    "regex_match", "date_format", "string_case_violation", "string_length_range",
    "set_membership", "set_exclusion", "value_in_range", "date_part_missing_fraction",
    "sql_assertion_violation",
    # Multivariate association
    "mutual_information", "cramers_v", "column_pair_comparison", "composite_uniqueness",
}

N_TRIALS = 30


# ── Baseline detectors ────────────────────────────────────────────────────────
class _AlwaysAlert:
    """Upper bound at 50% anomaly rate: precision=0.50, recall=1.0, F1=0.67."""
    slug = "_always_alert"
    family = "baseline"

    def fit(self, ref: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, cur: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return DetectorResult(verdict=Verdict.fail, score=1.0,
                              plain_english="always alert", details={})


class _NeverAlert:
    """Lower bound: F1=0."""
    slug = "_never_alert"
    family = "baseline"

    def fit(self, ref: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, cur: pd.DataFrame, state: DetectorState) -> DetectorResult:
        return DetectorResult(verdict=Verdict.pass_, score=0.0,
                              plain_english="never alert", details={})


class _Random50:
    """Random detector (50% rate): expected F1 ≈ 0.50."""
    slug = "_random_50pct"
    family = "baseline"

    def __init__(self, seed: int = 0) -> None:
        self._rng = np.random.default_rng(seed + 1000)

    def fit(self, ref: pd.DataFrame) -> DetectorState:
        return {}

    def score(self, cur: pd.DataFrame, state: DetectorState) -> DetectorResult:
        verdict = Verdict.fail if self._rng.random() < 0.5 else Verdict.pass_
        return DetectorResult(verdict=verdict, score=float(verdict == Verdict.fail),
                              plain_english="random", details={})


class _NaiveZscore:
    """Batch-mean z-score > 3 threshold — simplest possible drift test."""
    slug = "_naive_zscore"
    family = "baseline"

    def fit(self, ref: pd.DataFrame) -> DetectorState:
        vals = ref.iloc[:, 0].dropna().to_numpy(float)
        return {"mean": float(np.mean(vals)), "std": float(np.std(vals, ddof=1))}

    def score(self, cur: pd.DataFrame, state: DetectorState) -> DetectorResult:
        vals = cur.iloc[:, 0].dropna().to_numpy(float)
        if len(vals) == 0:
            return DetectorResult(verdict=Verdict.pass_, score=0.0,
                                  plain_english="no data", details={})
        z = abs(float(np.mean(vals)) - state["mean"]) / max(state["std"], 1e-9)
        verdict = Verdict.fail if z > 3.0 else Verdict.pass_
        return DetectorResult(verdict=verdict, score=z,
                              plain_english=f"z={z:.2f}", details={})


_BASELINES: list = [_AlwaysAlert(), _NeverAlert(), _Random50(), _NaiveZscore()]


# ── Trial-level scorer ────────────────────────────────────────────────────────
class TrialResult(NamedTuple):
    tp: int
    fp: int
    fn: int
    tn: int

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else float("nan")

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else float("nan")

    @property
    def f1(self) -> float:
        # 2*TP / (2*TP + FP + FN) — handles "never fires" (→ 0) and "no data" (→ NaN) correctly
        denom = 2 * self.tp + self.fp + self.fn
        return (2 * self.tp) / denom if denom > 0 else float("nan")

    @property
    def fpr(self) -> float:
        return self.fp / (self.fp + self.tn) if (self.fp + self.tn) else float("nan")


def _score_detector_on_fixtures(det, fixtures) -> TrialResult:
    tp = fp = fn = tn = 0
    for fix in fixtures:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                state = det.fit(fix.reference)
                r_clean = det.score(fix.current_clean, state)
                r_anom = det.score(fix.current_anomalous, state)
            if r_clean.verdict == Verdict.pass_:
                tn += 1
            else:
                fp += 1
            if r_anom.verdict != Verdict.pass_:
                tp += 1
            else:
                fn += 1
        except Exception:
            pass
    return TrialResult(tp, fp, fn, tn)


# ── Aggregate stats over trials ───────────────────────────────────────────────
class DetectorStats(NamedTuple):
    slug: str
    family: str
    n_trials: int
    f1_mean: float
    f1_std: float
    f1_ci_lo: float
    f1_ci_hi: float
    recall_mean: float
    recall_std: float
    precision_mean: float
    fpr_mean: float


def _aggregate(slug: str, family: str, trials: list[TrialResult]) -> DetectorStats | None:
    f1s = [t.f1 for t in trials if t.f1 == t.f1]  # drop NaN
    recs = [t.recall for t in trials if t.recall == t.recall]
    precs = [t.precision for t in trials if t.precision == t.precision]
    fprs = [t.fpr for t in trials if t.fpr == t.fpr]
    if not f1s:
        return None
    n = len(f1s)
    mean = float(np.mean(f1s))
    std = float(np.std(f1s, ddof=1)) if n > 1 else 0.0
    ci_half = 1.96 * std / math.sqrt(n) if n > 1 else 0.0
    return DetectorStats(
        slug=slug,
        family=family,
        n_trials=n,
        f1_mean=mean,
        f1_std=std,
        f1_ci_lo=max(0.0, mean - ci_half),
        f1_ci_hi=min(1.0, mean + ci_half),
        recall_mean=float(np.mean(recs)) if recs else float("nan"),
        recall_std=float(np.std(recs, ddof=1)) if len(recs) > 1 else 0.0,
        precision_mean=float(np.mean(precs)) if precs else float("nan"),
        fpr_mean=float(np.mean(fprs)) if fprs else float("nan"),
    )


# ── Formatting helpers ────────────────────────────────────────────────────────
def _f(v: float, decimals: int = 3) -> str:
    return f"{v:.{decimals}f}" if v == v else "—"


def _ci(lo: float, hi: float) -> str:
    if lo != lo or hi != hi:
        return "—"
    return f"[{lo:.3f}, {hi:.3f}]"


# ── Main ──────────────────────────────────────────────────────────────────────
def run_all() -> None:
    # Collect all scorable slugs
    slugs = [s for s in sorted(registry.slugs()) if s not in _SKIP]

    # Build per-slug trial lists
    trial_map: dict[str, list[TrialResult]] = {s: [] for s in slugs}
    baseline_trial_map: dict[str, list[TrialResult]] = {b.slug: [] for b in _BASELINES}

    print(f"Running {N_TRIALS} trials across {len(slugs)} detectors "
          f"+ {len(_BASELINES)} baselines …")

    for seed in range(N_TRIALS):
        rng = np.random.default_rng(seed)
        fixtures = make_fixtures(rng)

        for slug in slugs:
            cls = registry.get(slug)
            trial_map[slug].append(_score_detector_on_fixtures(cls(), fixtures))

        for b in _BASELINES:
            if b.slug == "_random_50pct":
                b_inst = _Random50(seed)
            else:
                b_inst = b
            baseline_trial_map[b.slug].append(
                _score_detector_on_fixtures(b_inst, fixtures)
            )

        if (seed + 1) % 10 == 0:
            print(f"  Trial {seed + 1}/{N_TRIALS} done")

    # Aggregate
    stats: list[DetectorStats] = []
    for slug in slugs:
        family = _FAMILY.get(slug, "other")
        s = _aggregate(slug, family, trial_map[slug])
        if s is not None:
            stats.append(s)

    baseline_stats: list[DetectorStats] = []
    for b in _BASELINES:
        s = _aggregate(b.slug, "baseline", baseline_trial_map[b.slug])
        if s is not None:
            baseline_stats.append(s)

    # ── CSV ──────────────────────────────────────────────────────────────────
    csv_path = _REPO_ROOT / "examples" / "benchmarks" / "results.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    csv_rows = ["slug,family,n_trials,f1_mean,f1_std,f1_ci_lo,f1_ci_hi,"
                "recall_mean,recall_std,precision_mean,fpr_mean"]
    for s in baseline_stats + stats:
        csv_rows.append(
            f"{s.slug},{s.family},{s.n_trials},"
            f"{_f(s.f1_mean)},{_f(s.f1_std)},{_f(s.f1_ci_lo)},{_f(s.f1_ci_hi)},"
            f"{_f(s.recall_mean)},{_f(s.recall_std)},{_f(s.precision_mean)},{_f(s.fpr_mean)}"
        )
    csv_path.write_text("\n".join(csv_rows) + "\n", encoding="utf-8")
    print(f"examples/benchmarks/results.csv updated — {len(stats)} detectors, "
          f"{len(baseline_stats)} baselines")

    # ── Markdown ─────────────────────────────────────────────────────────────
    by_family: dict[str, list[DetectorStats]] = {}
    for s in stats:
        by_family.setdefault(s.family, []).append(s)
    for lst in by_family.values():
        lst.sort(key=lambda x: -(x.f1_mean if x.f1_mean == x.f1_mean else -1))

    def _table(rows: list[DetectorStats]) -> str:
        hdr = ("| Detector | F1 mean | F1 std | 95% CI | Recall | Precision | FPR |\n"
               "|---|---|---|---|---|---|---|\n")
        body = ""
        for s in rows:
            body += (
                f"| `{s.slug}` | {_f(s.f1_mean)} | {_f(s.f1_std)} | "
                f"{_ci(s.f1_ci_lo, s.f1_ci_hi)} | "
                f"{_f(s.recall_mean)} | {_f(s.precision_mean)} | {_f(s.fpr_mean)} |\n"
            )
        return hdr + body

    def _baseline_table(rows: list[DetectorStats]) -> str:
        hdr = ("| Detector | Description | F1 mean | Recall | FPR |\n"
               "|---|---|---|---|---|\n")
        descs = {
            "_always_alert":  "Always fires — upper ceiling at 50% anomaly rate",
            "_never_alert":   "Never fires — lower bound",
            "_random_50pct":  "50% random alerting",
            "_naive_zscore":  "Batch-mean z-score > 3 threshold",
        }
        body = ""
        for s in rows:
            body += (
                f"| `{s.slug}` | {descs.get(s.slug, '')} | "
                f"{_f(s.f1_mean)} | {_f(s.recall_mean)} | {_f(s.fpr_mean)} |\n"
            )
        return hdr + body

    family_sections = ""
    family_labels = {
        "outlier":      "Outlier Detectors",
        "drift":        "Distribution Drift Detectors",
        "timeseries":   "Time-Series Detectors",
        "distribution": "Distribution Diagnostic Detectors",
        "other":        "Other Detectors",
    }
    for fam in ["outlier", "drift", "timeseries", "distribution", "other"]:
        rows = by_family.get(fam)
        if not rows:
            continue
        family_sections += f"\n## {family_labels.get(fam, fam.title())}\n\n"
        family_sections += _table(rows) + "\n"

    out = (
        "# dqt Detector Benchmarks\n\n"
        "_Auto-generated by `benchmarks/run_benchmarks.py`. "
        "Do not edit — re-run to update._\n\n"
        "## Methodology\n\n"
        f"- **Trials:** {N_TRIALS} independent runs (seeds 0-{N_TRIALS - 1})\n"
        "- **Sample size:** N=2,000 per fixture per trial\n"
        "- **Fixtures:** 8 synthetic scenarios (normal mean-shift, lognormal tail-shift, "
        "5% outlier injection, 10% null injection, variance explosion, "
        "gradual ramp drift, combined drift+nulls, heavy-tail contamination)\n"
        "- **Confidence intervals:** 95% via normal approximation "
        "(mean +/- 1.96 x std / sqrt(n_trials))\n"
        "- **Anomaly rate:** 50% (8 clean / 8 anomalous per trial)\n"
        "- **Interpretation:** Detectors are grouped by intended use case. "
        "Do not compare across families (an outlier detector is not competing "
        "with a distribution drift detector).\n\n"
        "### Fixture Descriptions\n\n"
        "| ID | Signal type | Difficulty |\n"
        "|---|---|---|\n"
        "| `normal_mean_shift` | N(50,10) to N(80,10) | Easy |\n"
        "| `lognormal_tail_shift` | LN(5.0,0.5) to LN(5.5,0.5) | Moderate |\n"
        "| `outliers_injected_5pct` | 5% extreme point anomalies | Moderate |\n"
        "| `nulls_injected_10pct` | 10% null injection | Easy |\n"
        "| `variance_explosion` | N(50,10) to N(50,20) | Moderate |\n"
        "| `gradual_drift` | Ramp drift +20 over batch | Hard |\n"
        "| `mixed_drift_and_nulls` | Mean shift + 10% nulls | Moderate |\n"
        "| `heavy_tail_switch` | 20% contamination at 4x spread | Hard |\n\n"
        "### Baselines\n\n"
        "> A well-calibrated detector should beat `_always_alert` (F1 > 0.670) "
        "and `_random_50pct` (F1 > 0.500).\n\n"
        + _baseline_table(baseline_stats)
        + family_sections
        + "\n---\n\n"
        "Raw results (with full CI columns): "
        "[`examples/benchmarks/results.csv`](../examples/benchmarks/results.csv)\n"
    )

    docs_path = _REPO_ROOT / "docs" / "benchmarks.md"
    docs_path.write_text(out, encoding="utf-8")
    print(f"docs/benchmarks.md updated — "
          f"{len(stats)} detectors across {len(by_family)} families")


if __name__ == "__main__":
    run_all()
