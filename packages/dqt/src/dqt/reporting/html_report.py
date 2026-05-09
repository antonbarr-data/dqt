"""Self-contained HTML report generator for dqt profiling and quality check results.

No external template dependencies — HTML is generated via Python f-strings.
Charts require the optional dqt[reports] extra (matplotlib>=3.8).
"""
from __future__ import annotations

import html as _html
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dqt.profiling.models import DatasetProfile

# ── Design tokens ─────────────────────────────────────────────────────────────
_ACCENT = "#9DD0B0"
_PASS = "#7FB394"
_WARN = "#D9B566"
_FAIL = "#E07B6E"
_BG0 = "#0F1117"
_BG1 = "#161B25"
_BG2 = "#1E2433"
_FG0 = "#E8EAF0"
_FG1 = "#A0A8B8"
_FG2 = "#666E82"
_LINE = "#2A3147"

# ── Shared CSS ────────────────────────────────────────────────────────────────
_CSS = f"""
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{
  background: {_BG0}; color: {_FG0};
  font-family: Inter, system-ui, sans-serif;
  font-size: 13px; line-height: 1.5;
}}
header {{
  padding: 20px 28px 16px;
  border-bottom: 1px solid {_LINE};
  display: flex; flex-direction: column; gap: 4px;
}}
.brand {{
  font-family: 'JetBrains Mono', monospace; font-weight: 300;
  font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase;
  color: {_ACCENT};
}}
h1 {{ font-size: 18px; font-weight: 500; color: {_FG0}; }}
.meta {{ font-size: 11px; color: {_FG2}; font-family: 'JetBrains Mono', monospace; }}
.ai-summary {{
  margin: 16px 28px; padding: 14px 16px;
  background: {_BG1}; border: 1px solid {_LINE};
  border-left: 3px solid {_ACCENT};
  font-size: 12px; color: {_FG1};
}}
.ai-summary-label {{
  font-size: 10px; text-transform: uppercase; letter-spacing: 0.12em;
  color: {_ACCENT}; margin-bottom: 6px;
  font-family: 'JetBrains Mono', monospace;
}}
.summary-bar {{
  display: flex; gap: 1px;
  margin: 0 28px 16px; border: 1px solid {_LINE};
}}
.summary-stat {{
  flex: 1; padding: 10px 14px; background: {_BG1};
}}
.summary-stat .label {{
  font-size: 10px; text-transform: uppercase; letter-spacing: 0.12em;
  color: {_FG2}; font-family: 'JetBrains Mono', monospace;
}}
.summary-stat .value {{
  font-size: 22px; font-weight: 300;
  font-family: 'JetBrains Mono', monospace; color: {_FG0};
}}
.profile-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(540px, 1fr));
  gap: 1px; margin: 0 28px 28px;
  border: 1px solid {_LINE};
}}
.col-card {{
  background: {_BG1}; padding: 14px 16px;
}}
.col-header {{
  display: flex; align-items: center; gap: 8px; margin-bottom: 10px;
}}
.col-name {{
  font-family: 'JetBrains Mono', monospace; font-weight: 400;
  font-size: 13px; color: {_FG0};
}}
.badge {{
  font-size: 10px; padding: 2px 6px;
  font-family: 'JetBrains Mono', monospace; letter-spacing: 0.05em;
  border: 1px solid {_LINE}; color: {_FG2};
}}
.badge-pass {{ background: #1A2E24; color: {_PASS}; border-left: 3px solid {_PASS}; }}
.badge-warn {{ background: #2E2A1A; color: {_WARN}; border-left: 3px solid {_WARN}; }}
.badge-fail {{ background: #2E1A1A; color: {_FAIL}; border-left: 3px solid {_FAIL}; }}
.stats-row {{
  display: flex; gap: 16px; margin-bottom: 10px;
}}
.stat-item .label {{
  font-size: 10px; text-transform: uppercase; letter-spacing: 0.12em;
  color: {_FG2}; font-family: 'JetBrains Mono', monospace;
}}
.stat-item .value {{
  font-size: 13px; font-family: 'JetBrains Mono', monospace; color: {_FG1};
}}
.stats-table {{
  width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 8px;
}}
.stats-table th, .stats-table td {{
  padding: 4px 8px; border: 1px solid {_LINE};
  font-family: 'JetBrains Mono', monospace; text-align: right;
}}
.stats-table th {{ color: {_FG2}; background: {_BG2}; font-weight: 400; }}
.stats-table td {{ color: {_FG1}; }}
.chart-img {{ display: block; max-width: 100%; margin-top: 8px; }}
/* Quality report table */
.dq-table {{
  width: calc(100% - 56px); margin: 0 28px 28px; border-collapse: collapse;
  font-size: 12px;
}}
.dq-table th {{
  padding: 6px 10px; border: 1px solid {_LINE};
  background: {_BG2}; color: {_FG2};
  font-family: 'JetBrains Mono', monospace; font-weight: 400;
  text-transform: uppercase; letter-spacing: 0.08em; font-size: 10px;
  text-align: left;
}}
.dq-table td {{
  padding: 6px 10px; border: 1px solid {_LINE}; color: {_FG1};
}}
.dq-table tr.pass td {{ background: #141e18; }}
.dq-table tr.warn td {{ background: #1e1c12; }}
.dq-table tr.fail td {{ background: #1e1212; }}
.dq-table tr:hover td {{ filter: brightness(1.15); }}
.verdict-pass {{ color: {_PASS}; font-family: 'JetBrains Mono', monospace; font-size: 10px; }}
.verdict-warn {{ color: {_WARN}; font-family: 'JetBrains Mono', monospace; font-size: 10px; }}
.verdict-fail {{ color: {_FAIL}; font-family: 'JetBrains Mono', monospace; font-size: 10px; }}
.score {{ font-family: 'JetBrains Mono', monospace; }}
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def _e(text: object) -> str:
    """HTML-escape a value for safe insertion."""
    return _html.escape(str(text))


def _null_badge(null_pct: float) -> str:
    if null_pct < 1.0:
        cls = "badge-pass"
    elif null_pct <= 5.0:
        cls = "badge-warn"
    else:
        cls = "badge-fail"
    return f'<span class="badge {cls}">{null_pct:.1f}% null</span>'


def _verdict_badge(verdict: str) -> str:
    v = verdict.lower()
    if v == "pass":
        return f'<span class="verdict-pass">PASS</span>'
    if v == "warn":
        return f'<span class="verdict-warn">WARN</span>'
    return f'<span class="verdict-fail">FAIL</span>'


def _html_page(title: str, body: str) -> str:
    return (
        f'<!DOCTYPE html>\n<html data-theme="dark">\n<head>\n'
        f'  <meta charset="utf-8">\n  <title>{_e(title)}</title>\n'
        f'  <style>{_CSS}</style>\n</head>\n<body>\n{body}\n</body>\n</html>'
    )


def _ai_section(ai_summary: str) -> str:
    if not ai_summary.strip():
        return ""
    return (
        f'<div class="ai-summary">'
        f'<div class="ai-summary-label">AI Summary</div>'
        f'{_e(ai_summary)}'
        f'</div>'
    )


def _summary_bar(**stats: object) -> str:
    items = "".join(
        f'<div class="summary-stat">'
        f'<div class="label">{_e(label)}</div>'
        f'<div class="value">{_e(value)}</div>'
        f'</div>'
        for label, value in stats.items()
    )
    return f'<div class="summary-bar">{items}</div>'


# ── Column card ───────────────────────────────────────────────────────────────

def _column_card(col: "ColumnProfile") -> str:  # type: ignore[name-defined]
    # Lazy import — matplotlib required only if charts are rendered
    try:
        from dqt.reporting._charts import histogram_chart, distribution_bars
        _charts_available = True
    except ImportError:
        _charts_available = False

    badges = (
        f'<span class="badge">{_e(col.data_type)}</span>'
        f'<span class="badge">{_e(col.distribution_type)}</span>'
        f'{_null_badge(col.null_pct)}'
    )
    header = (
        f'<div class="col-header">'
        f'<span class="col-name">{_e(col.name)}</span>'
        f'{badges}'
        f'</div>'
    )

    stats_row = (
        f'<div class="stats-row">'
        f'<div class="stat-item"><div class="label">Nulls</div>'
        f'<div class="value">{col.null_pct:.2f}%</div></div>'
        f'<div class="stat-item"><div class="label">Unique</div>'
        f'<div class="value">{col.unique_pct:.2f}%</div></div>'
        f'<div class="stat-item"><div class="label">Rows</div>'
        f'<div class="value">{col.total_count:,}</div></div>'
        f'</div>'
    )

    detail = ""

    if col.numeric_stats is not None:
        ns = col.numeric_stats
        detail += (
            f'<table class="stats-table"><thead><tr>'
            f'<th>min</th><th>q25</th><th>median</th><th>mean</th><th>q75</th><th>max</th><th>std</th>'
            f'</tr></thead><tbody><tr>'
            f'<td>{ns.min:.4g}</td><td>{ns.q25:.4g}</td><td>{ns.median:.4g}</td>'
            f'<td>{ns.mean:.4g}</td><td>{ns.q75:.4g}</td><td>{ns.max:.4g}</td><td>{ns.std:.4g}</td>'
            f'</tr></tbody></table>'
        )
        if _charts_available and col.histogram:
            centers = [(b.left + b.right) / 2 for b in col.histogram for _ in range(b.count)]
            if centers:
                b64 = histogram_chart(centers, title=col.name, width=520, height=160)
                detail += f'<img class="chart-img" src="data:image/png;base64,{b64}" alt="histogram">'

    elif col.top_values:
        labels = [tv.value for tv in col.top_values]
        values = [tv.pct for tv in col.top_values]
        if _charts_available:
            b64 = distribution_bars(labels, values, title=f"{col.name} — top values", width=520, height=160)
            detail += f'<img class="chart-img" src="data:image/png;base64,{b64}" alt="top values">'
        else:
            # Fallback: plain text list
            rows = "".join(
                f'<tr><td>{_e(tv.value)}</td><td>{tv.count:,}</td><td>{tv.pct:.1f}%</td></tr>'
                for tv in col.top_values
            )
            detail += (
                f'<table class="stats-table"><thead><tr>'
                f'<th style="text-align:left">Value</th><th>Count</th><th>%</th>'
                f'</tr></thead><tbody>{rows}</tbody></table>'
            )
        if col.string_stats is not None:
            ss = col.string_stats
            detail += (
                f'<div style="margin-top:8px;font-size:11px;color:{_FG2};'
                f'font-family:\'JetBrains Mono\',monospace;">'
                f'len: min={ss.min_length} avg={ss.avg_length:.1f} '
                f'median={ss.median_length:.1f} max={ss.max_length}'
                f'</div>'
            )

    elif col.bool_stats is not None:
        bs = col.bool_stats
        detail += (
            f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:11px;color:{_FG1};">'
            f'true: {bs.true_count:,} ({bs.true_pct:.1f}%) &nbsp;|&nbsp; '
            f'false: {bs.false_count:,}'
            f'</div>'
        )

    elif col.date_stats is not None:
        ds = col.date_stats
        detail += (
            f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:11px;color:{_FG1};">'
            f'range: {_e(ds.min)} → {_e(ds.max)} ({ds.date_range_days} days)'
            f'</div>'
        )

    return f'<div class="col-card">{header}{stats_row}{detail}</div>'


# ── Public API ────────────────────────────────────────────────────────────────

def profiling_report(
    profile: "DatasetProfile",
    title: str = "Data Profiling Report",
    ai_summary: str = "",
) -> str:
    """Generate a self-contained HTML profiling report."""
    dataset_name = f"{profile.schema_name}.{profile.table_name}"

    header = (
        f'<header>'
        f'<div class="brand">dqt</div>'
        f'<h1>{_e(title)}</h1>'
        f'<div class="meta">'
        f'{_e(dataset_name)} · {profile.row_count:,} rows · {profile.column_count} columns'
        f' · profiled {_e(profile.profiled_at)}'
        f'</div>'
        f'</header>'
    )

    avg_null = sum(c.null_pct for c in profile.columns) / max(len(profile.columns), 1)
    avg_unique = sum(c.unique_pct for c in profile.columns) / max(len(profile.columns), 1)

    summary = _summary_bar(
        **{
            "Columns": profile.column_count,
            "Rows": f"{profile.row_count:,}",
            "Avg null %": f"{avg_null:.1f}%",
            "Avg unique %": f"{avg_unique:.1f}%",
        }
    )

    cards = "\n".join(_column_card(col) for col in profile.columns)
    grid = f'<div class="profile-grid">{cards}</div>'

    body = f"{header}\n{_ai_section(ai_summary)}\n{summary}\n{grid}"
    return _html_page(title, body)


def quality_report(
    results: list[dict],
    dataset_name: str = "Dataset",
    title: str = "Data Quality Report",
    ai_summary: str = "",
) -> str:
    """Generate a self-contained HTML DQ check results report."""
    from datetime import datetime, timezone
    run_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    verdicts = [r.get("verdict", "").lower() for r in results]
    n_pass = sum(1 for v in verdicts if v == "pass")
    n_warn = sum(1 for v in verdicts if v == "warn")
    n_fail = sum(1 for v in verdicts if v == "fail")
    n_total = len(results)

    header = (
        f'<header>'
        f'<div class="brand">dqt</div>'
        f'<h1>{_e(title)}</h1>'
        f'<div class="meta">'
        f'{_e(dataset_name)} · {n_total} checks · run {_e(run_at)}'
        f'</div>'
        f'</header>'
    )

    summary = _summary_bar(
        **{
            "Total": n_total,
            "Pass": n_pass,
            "Warn": n_warn,
            "Fail": n_fail,
        }
    )

    rows = ""
    for r in results:
        verdict = r.get("verdict", "")
        score_raw = r.get("score", "")
        try:
            score_str = f"{float(score_raw):.4f}"
        except (TypeError, ValueError):
            score_str = _e(score_raw)

        row_cls = verdict.lower() if verdict.lower() in ("pass", "warn", "fail") else ""
        rows += (
            f'<tr class="{row_cls}">'
            f'<td>{_e(r.get("check", ""))}</td>'
            f'<td style="font-family:\'JetBrains Mono\',monospace;">{_e(r.get("table", ""))}</td>'
            f'<td style="font-family:\'JetBrains Mono\',monospace;">{_e(r.get("column", ""))}</td>'
            f'<td class="score">{score_str}</td>'
            f'<td>{_verdict_badge(verdict)}</td>'
            f'<td>{_e(r.get("plain_english", ""))}</td>'
            f'</tr>'
        )

    table = (
        f'<table class="dq-table">'
        f'<thead><tr>'
        f'<th>Check</th><th>Table</th><th>Column</th>'
        f'<th>Score</th><th>Verdict</th><th>Summary</th>'
        f'</tr></thead>'
        f'<tbody>{rows}</tbody>'
        f'</table>'
    )

    body = f"{header}\n{_ai_section(ai_summary)}\n{summary}\n{table}"
    return _html_page(title, body)


def save_report(html: str, path: str) -> None:
    """Write HTML to file."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
