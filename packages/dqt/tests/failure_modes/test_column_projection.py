# packages/dqt/tests/failure_modes/test_column_projection.py
"""Every sample-kind detector on column N must score column N, not column 0."""
import numpy as np
import pandas as pd
import pytest

SLUGS_TO_TEST = [
    "wasserstein_1", "ks_pvalue", "iqr_fence",
    "mad_outlier_fraction", "adwin",
]


@pytest.mark.parametrize("slug", SLUGS_TO_TEST)
def test_detector_scores_correct_column(slug):
    """A detector asked to score column 'target' must not silently score column 'noise'."""
    import dqt  # trigger registry registration
    from dqt.algorithms._registry import registry

    rng = np.random.default_rng(0)
    ref = pd.DataFrame({
        "noise": rng.normal(0, 1, 300),
        "target": rng.normal(0, 1, 300),
    })
    curr = pd.DataFrame({
        "noise": rng.normal(0, 1, 300),
        "target": rng.normal(10, 1, 300),
    })

    cls = registry.get(slug)
    det = cls()
    state = det.fit(ref[["target"]])
    result = det.score(curr[["target"]], state)
    assert result.verdict.value in ("warn", "fail"), (
        f"{slug}: should detect a 10-sigma shift in 'target' but got {result.verdict} "
        f"(score={result.score:.4f})"
    )
