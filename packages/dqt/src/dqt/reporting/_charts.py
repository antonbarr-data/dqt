"""Matplotlib chart helpers returning base64-encoded PNG strings for HTML reports.

All charts use the dqt dark theme. matplotlib is an optional dep (dqt[reports]).
"""
from __future__ import annotations

import base64
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402 (must be after matplotlib.use)

# dqt dark theme applied globally for this module
plt.rcParams.update({
    "figure.facecolor": "#0F1117",
    "axes.facecolor": "#161B25",
    "axes.edgecolor": "#2A3147",
    "grid.color": "#2A3147",
    "text.color": "#A0A8B8",
    "xtick.color": "#666E82",
    "ytick.color": "#666E82",
    "font.family": "monospace",
})

_DPI = 96


def _fig_to_b64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=_DPI)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def histogram_chart(
    data: list[float],
    title: str,
    color: str = "#9DD0B0",
    width: int = 600,
    height: int = 200,
) -> str:
    """Render a histogram as base64 PNG. Dark background."""
    fig, ax = plt.subplots(figsize=(width / _DPI, height / _DPI))
    if data:
        n_bins = min(30, max(5, len(set(data))))
        ax.hist(data, bins=n_bins, color=color, edgecolor="#2A3147", linewidth=0.5)
    ax.set_title(title, fontsize=9, pad=4)
    ax.tick_params(labelsize=7)
    ax.grid(axis="y", linewidth=0.4, alpha=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout(pad=0.4)
    return _fig_to_b64(fig)


def distribution_bars(
    labels: list[str],
    values: list[float],
    title: str,
    width: int = 600,
    height: int = 200,
) -> str:
    """Render a horizontal bar chart for top_values. Dark background."""
    fig, ax = plt.subplots(figsize=(width / _DPI, height / _DPI))
    if labels and values:
        # Show at most 10 bars; truncate long labels
        disp_labels = [str(l)[:20] for l in labels[:10]]
        disp_values = values[:10]
        colors = ["#9DD0B0"] * len(disp_labels)
        bars = ax.barh(range(len(disp_labels)), disp_values, color=colors, edgecolor="#2A3147", linewidth=0.5)
        ax.set_yticks(range(len(disp_labels)))
        ax.set_yticklabels(disp_labels, fontsize=7)
        ax.invert_yaxis()
        # Value labels on bars
        for bar, val in zip(bars, disp_values):
            ax.text(
                bar.get_width() + max(disp_values) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%",
                va="center", ha="left", fontsize=6, color="#A0A8B8",
            )
    ax.set_title(title, fontsize=9, pad=4)
    ax.tick_params(axis="x", labelsize=7)
    ax.grid(axis="x", linewidth=0.4, alpha=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout(pad=0.4)
    return _fig_to_b64(fig)


def time_series_chart(
    dates: list[str],
    values: list[float],
    title: str,
    color: str = "#9DD0B0",
    width: int = 800,
    height: int = 200,
) -> str:
    """Render a time series line chart as base64 PNG. Dark background."""
    fig, ax = plt.subplots(figsize=(width / _DPI, height / _DPI))
    if dates and values:
        ax.plot(range(len(values)), values, color=color, linewidth=1.2)
        # Show a subset of x-tick labels to avoid crowding
        step = max(1, len(dates) // 8)
        ticks = list(range(0, len(dates), step))
        ax.set_xticks(ticks)
        ax.set_xticklabels([dates[i] for i in ticks], rotation=30, ha="right", fontsize=6)
    ax.set_title(title, fontsize=9, pad=4)
    ax.tick_params(axis="y", labelsize=7)
    ax.grid(linewidth=0.4, alpha=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout(pad=0.4)
    return _fig_to_b64(fig)


def correlation_heatmap(
    labels: list[str],
    matrix: list[list[float]],
    title: str,
    width: int = 500,
    height: int = 500,
) -> str:
    """Render a correlation heatmap as base64 PNG."""
    import numpy as np

    fig, ax = plt.subplots(figsize=(width / _DPI, height / _DPI))
    if labels and matrix:
        arr = np.array(matrix)
        im = ax.imshow(arr, cmap="RdYlGn", vmin=-1, vmax=1, aspect="auto")
        fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
        ax.set_xticks(range(len(labels)))
        ax.set_yticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
        ax.set_yticklabels(labels, fontsize=7)
        # Annotate cells
        for i in range(len(labels)):
            for j in range(len(labels)):
                ax.text(j, i, f"{arr[i, j]:.2f}", ha="center", va="center", fontsize=6, color="#E8EAF0")
    ax.set_title(title, fontsize=9, pad=4)
    fig.tight_layout(pad=0.4)
    return _fig_to_b64(fig)
