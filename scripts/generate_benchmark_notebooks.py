#!/usr/bin/env python3
"""Generate benchmark notebooks for each detector group."""
import sys
from pathlib import Path
import nbformat as nbf

_REPO = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO / "packages" / "dqt" / "src"))

# Import all algorithm modules to populate the registry
import dqt.algorithms.basic  # noqa: F401
import dqt.algorithms.outliers_uni  # noqa: F401
import dqt.algorithms.outliers_multi  # noqa: F401
import dqt.algorithms.drift  # noqa: F401
import dqt.algorithms.timeseries  # noqa: F401
import dqt.algorithms.info  # noqa: F401
import dqt.algorithms.referential  # noqa: F401
import dqt.algorithms.schema  # noqa: F401
import dqt.algorithms.pattern  # noqa: F401
import dqt.algorithms.custom  # noqa: F401

from dqt.algorithms._registry import registry

RESULTS_CSV = _REPO / "examples" / "benchmarks" / "results.csv"
OUT_DIR = _REPO / "examples" / "benchmarks"

NOTEBOOKS = [
    ("01_outliers_univariate.ipynb", ["outliers_uni"], "Outliers - Univariate",
     "Detectors for point outliers in single numeric columns."),
    ("02_outliers_multivariate.ipynb", ["outliers_multi"], "Outliers - Multivariate",
     "Detectors for outlier rows in multi-dimensional numeric feature spaces."),
    ("03_drift_distribution.ipynb", ["drift"], "Distribution Drift",
     "Detectors measuring distributional shift between a reference and current window."),
    ("04_changepoint_timeseries.ipynb", ["timeseries"], "Time Series & Changepoints",
     "Detectors for level shifts, trend breaks, and seasonal anomalies in time series."),
    ("05_association.ipynb", ["info"], "Association & Information",
     "Detectors measuring correlation and mutual information between columns."),
    ("06_basic.ipynb", ["basic"], "Basic Checks",
     "Aggregate-based checks for volume, completeness, freshness, range, and format."),
    ("07_referential_schema_pattern.ipynb", ["referential", "schema", "pattern"],
     "Referential, Schema & Pattern",
     "Detectors for referential integrity, schema drift, and Benford law compliance."),
    ("08_custom.ipynb", ["custom"], "Custom Checks",
     "Detectors for user-defined callable and remote endpoint checks."),
]

def make_notebook(fname, groups, title, description):
    """Create a benchmark notebook for the given groups."""
    nb = nbf.v4.new_notebook()

    # Filter detectors by group
    slugs_in_groups = [
        s for s in registry.slugs()
        if registry.get(s).group in groups
    ]
    slugs_in_groups = sorted(slugs_in_groups)

    # Title and description
    title_cell = nbf.v4.new_markdown_cell(
        f"# {title} Benchmark Results\n\n{description}"
    )

    # Load and display results
    code_cell_1 = nbf.v4.new_code_cell(
        "import pandas as pd\n"
        "import matplotlib.pyplot as plt\n"
        "from pathlib import Path\n\n"
        f"GROUPS = {groups!r}\n"
        "df = pd.read_csv(Path('../../examples/benchmarks/results.csv'))\n"
        f"slugs = {slugs_in_groups!r}\n"
        "df = df[df['detector_slug'].isin(slugs)].sort_values('f1', ascending=False)\n"
        "display(df[['detector_slug','dataset','precision','recall','f1','wall_time_s']])"
    )

    # Bar chart of F1 scores
    code_cell_2 = nbf.v4.new_code_cell(
        "fig, ax = plt.subplots(figsize=(10, max(3, len(df)*0.35)))\n"
        "colors = ['#7FB394' if f >= 0.8 else '#D9B566' if f >= 0.6 else '#E07B6E' for f in df['f1']]\n"
        "ax.barh(df['detector_slug'], df['f1'], color=colors)\n"
        "ax.axvline(0.8, color='#7FB394', linestyle='--', alpha=0.7, label='F1=0.8')\n"
        "ax.axvline(0.6, color='#D9B566', linestyle='--', alpha=0.7, label='F1=0.6')\n"
        f"ax.set_title('{title} — F1 Scores')\n"
        "ax.set_xlabel('F1')\n"
        "ax.set_xlim(0, 1.05)\n"
        "ax.legend()\n"
        "plt.tight_layout()\n"
        "plt.show()"
    )

    nb.cells = [title_cell, code_cell_1, code_cell_2]
    return nb

# Create all notebooks
for fname, groups, title, desc in NOTEBOOKS:
    nb = make_notebook(fname, groups, title, desc)
    path = OUT_DIR / fname
    with open(str(path), 'w') as f:
        nbf.write(nb, f)
    print(f"  {path}")

print("Done.")
