"""Self-contained HTML report generator for dqt profiling and quality check results.

No external template dependencies — HTML is generated via Python f-strings.
Charts require the optional dqt[reports] extra (matplotlib>=3.8).
Light theme is the default; a theme toggle button switches to dark in the browser.
"""
from __future__ import annotations

import html as _html
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dqt.profiling.models import DatasetProfile

# ── CSS: design tokens + shared rules ─────────────────────────────────────────
_CSS = """
:root {
  --bg-0: #FFFFFF; --bg-1: #F5F7FA; --bg-2: #EDF0F5;
  --fg-0: #1A1F2E; --fg-1: #3D4663; --fg-2: #8892A4;
  --line: #DDE1EC;
  --accent: #1E8A52; --pass: #1E7A4A; --warn: #9A7220; --fail: #C44D40;
  --badge-pass-bg: #E8F5EE; --badge-warn-bg: #FAF4E0; --badge-fail-bg: #FAE8E6;
  --row-pass: #F2FAF5; --row-warn: #FAF7EC; --row-fail: #FAF0EF;
}
[data-theme="dark"] {
  --bg-0: #0F1117; --bg-1: #161B25; --bg-2: #1E2433;
  --fg-0: #E8EAF0; --fg-1: #A0A8B8; --fg-2: #666E82;
  --line: #2A3147;
  --accent: #9DD0B0; --pass: #7FB394; --warn: #D9B566; --fail: #E07B6E;
  --badge-pass-bg: #1A2E24; --badge-warn-bg: #2E2A1A; --badge-fail-bg: #2E1A1A;
  --row-pass: #141e18; --row-warn: #1e1c12; --row-fail: #1e1212;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body {
  background: var(--bg-0); color: var(--fg-0);
  font-family: Inter, system-ui, sans-serif;
  font-size: 13px; line-height: 1.5;
}
header {
  position: relative;
  padding: 20px 28px 16px;
  border-bottom: 1px solid var(--line);
  display: flex; flex-direction: column; gap: 4px;
}
.brand {
  font-family: 'JetBrains Mono', monospace; font-weight: 300;
  font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase;
  color: var(--accent);
}
h1 { font-size: 18px; font-weight: 500; color: var(--fg-0); }
.meta { font-size: 11px; color: var(--fg-2); font-family: 'JetBrains Mono', monospace; }
#theme-btn {
  position: absolute; top: 16px; right: 20px;
  background: none; border: 1px solid var(--line); color: var(--fg-2);
  cursor: pointer; padding: 4px 10px; font-family: 'JetBrains Mono', monospace;
  font-size: 11px; letter-spacing: 0.05em;
}
.ai-summary {
  margin: 16px 28px; padding: 14px 16px;
  background: var(--bg-1); border: 1px solid var(--line);
  border-left: 3px solid var(--accent);
  font-size: 12px; color: var(--fg-1);
}
.ai-summary-label {
  font-size: 10px; text-transform: uppercase; letter-spacing: 0.12em;
  color: var(--accent); margin-bottom: 6px;
  font-family: 'JetBrains Mono', monospace;
}
.summary-bar {
  display: flex; gap: 1px;
  margin: 0 28px 16px; border: 1px solid var(--line);
}
.summary-stat {
  flex: 1; padding: 10px 14px; background: var(--bg-1);
}
.summary-stat .label {
  font-size: 10px; text-transform: uppercase; letter-spacing: 0.12em;
  color: var(--fg-2); font-family: 'JetBrains Mono', monospace;
}
.summary-stat .value {
  font-size: 22px; font-weight: 300;
  font-family: 'JetBrains Mono', monospace; color: var(--fg-0);
}
.profile-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(540px, 1fr));
  gap: 1px; margin: 0 28px 28px;
  border: 1px solid var(--line);
}
.col-card {
  background: var(--bg-1); padding: 14px 16px;
}
.col-header {
  display: flex; align-items: center; gap: 8px; margin-bottom: 10px;
}
.col-name {
  font-family: 'JetBrains Mono', monospace; font-weight: 400;
  font-size: 13px; color: var(--fg-0);
}
.badge {
  font-size: 10px; padding: 2px 6px;
  font-family: 'JetBrains Mono', monospace; letter-spacing: 0.05em;
  border: 1px solid var(--line); color: var(--fg-2);
}
.badge-pass { background: var(--badge-pass-bg); color: var(--pass); border-left: 3px solid var(--pass); }
.badge-warn { background: var(--badge-warn-bg); color: var(--warn); border-left: 3px solid var(--warn); }
.badge-fail { background: var(--badge-fail-bg); color: var(--fail); border-left: 3px solid var(--fail); }
.stats-row {
  display: flex; gap: 16px; margin-bottom: 10px;
}
.stat-item .label {
  font-size: 10px; text-transform: uppercase; letter-spacing: 0.12em;
  color: var(--fg-2); font-family: 'JetBrains Mono', monospace;
}
.stat-item .value {
  font-size: 13px; font-family: 'JetBrains Mono', monospace; color: var(--fg-1);
}
.stats-table {
  width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 8px;
}
.stats-table th, .stats-table td {
  padding: 4px 8px; border: 1px solid var(--line);
  font-family: 'JetBrains Mono', monospace; text-align: right;
}
.stats-table th { color: var(--fg-2); background: var(--bg-2); font-weight: 400; }
.stats-table td { color: var(--fg-1); }
.chart-img { display: block; max-width: 100%; margin-top: 8px; }
/* Quality report table */
.dq-table {
  width: calc(100% - 56px); margin: 0 28px 28px; border-collapse: collapse;
  font-size: 12px;
}
.dq-table th {
  padding: 6px 10px; border: 1px solid var(--line);
  background: var(--bg-2); color: var(--fg-2);
  font-family: 'JetBrains Mono', monospace; font-weight: 400;
  text-transform: uppercase; letter-spacing: 0.08em; font-size: 10px;
  text-align: left;
}
.dq-table td {
  padding: 6px 10px; border: 1px solid var(--line); color: var(--fg-1);
}
.dq-table tr.pass td { background: var(--row-pass); }
.dq-table tr.warn td { background: var(--row-warn); }
.dq-table tr.fail td { background: var(--row-fail); }
.dq-table tr:hover td { filter: brightness(1.05); }
.verdict-pass { color: var(--pass); font-family: 'JetBrains Mono', monospace; font-size: 10px; }
.verdict-warn { color: var(--warn); font-family: 'JetBrains Mono', monospace; font-size: 10px; }
.verdict-fail { color: var(--fail); font-family: 'JetBrains Mono', monospace; font-size: 10px; }
.score { font-family: 'JetBrains Mono', monospace; }
.bool-stats, .date-stats {
  font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--fg-1);
}
.string-meta {
  margin-top: 8px; font-size: 11px;
  font-family: 'JetBrains Mono', monospace; color: var(--fg-2);
}
"""

# ── Theme JS ──────────────────────────────────────────────────────────────────
_THEME_JS = """
<script>
function toggleTheme() {
  var html = document.documentElement;
  var current = html.getAttribute('data-theme') || 'light';
  var next = current === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('dqt-theme', next);
  document.querySelectorAll('.chart-light').forEach(function(el) {
    el.style.display = next === 'dark' ? 'none' : '';
  });
  document.querySelectorAll('.chart-dark').forEach(function(el) {
    el.style.display = next === 'light' ? 'none' : '';
  });
}
(function() {
  var saved = localStorage.getItem('dqt-theme');
  if (saved) {
    document.documentElement.setAttribute('data-theme', saved);
    if (saved === 'dark') {
      document.addEventListener('DOMContentLoaded', function() {
        document.querySelectorAll('.chart-light').forEach(function(el) {
          el.style.display = 'none';
        });
        document.querySelectorAll('.chart-dark').forEach(function(el) {
          el.style.display = '';
        });
      });
    }
  }
})();
</script>
"""

_THEME_BTN = (
    '<button id="theme-btn" onclick="toggleTheme()" title="Toggle theme">'
    '◐ theme'
    '</button>'
)


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
        return '<span class="verdict-pass">PASS</span>'
    if v == "warn":
        return '<span class="verdict-warn">WARN</span>'
    return '<span class="verdict-fail">FAIL</span>'


def _html_page(title: str, body: str, initial_theme: str = "light") -> str:
    return (
        f'<!DOCTYPE html>\n<html data-theme="{initial_theme}">\n<head>\n'
        f'  <meta charset="utf-8">\n  <title>{_e(title)}</title>\n'
        f'  <style>{_CSS}</style>\n</head>\n<body>\n{body}\n{_THEME_JS}</body>\n</html>'
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


def _dual_chart_imgs(b64_light: str, b64_dark: str, alt: str) -> str:
    """Render two chart images for light/dark — JS toggles visibility."""
    return (
        f'<img class="chart-img chart-light" src="data:image/png;base64,{b64_light}" alt="{_e(alt)}">'
        f'<img class="chart-img chart-dark"  src="data:image/png;base64,{b64_dark}"  alt="{_e(alt)}" style="display:none">'
    )


# ── Column card ───────────────────────────────────────────────────────────────

def _column_card(col: "ColumnProfile") -> str:  # type: ignore[name-defined]
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
                b64_light = histogram_chart(centers, title=col.name, theme="light", width=520, height=160)
                b64_dark  = histogram_chart(centers, title=col.name, theme="dark",  width=520, height=160)
                detail += _dual_chart_imgs(b64_light, b64_dark, "histogram")

    elif col.top_values:
        labels = [tv.value for tv in col.top_values]
        values = [tv.pct for tv in col.top_values]
        if _charts_available:
            b64_light = distribution_bars(labels, values, title=f"{col.name} — top values", theme="light", width=520, height=160)
            b64_dark  = distribution_bars(labels, values, title=f"{col.name} — top values", theme="dark",  width=520, height=160)
            detail += _dual_chart_imgs(b64_light, b64_dark, "top values")
        else:
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
                f'<div class="string-meta">'
                f'len: min={ss.min_length} avg={ss.avg_length:.1f} '
                f'median={ss.median_length:.1f} max={ss.max_length}'
                f'</div>'
            )

    elif col.bool_stats is not None:
        bs = col.bool_stats
        detail += (
            f'<div class="bool-stats">'
            f'true: {bs.true_count:,} ({bs.true_pct:.1f}%) &nbsp;|&nbsp; '
            f'false: {bs.false_count:,}'
            f'</div>'
        )

    elif col.date_stats is not None:
        ds = col.date_stats
        detail += (
            f'<div class="date-stats">'
            f'range: {_e(ds.min)} → {_e(ds.max)} ({ds.date_range_days} days)'
            f'</div>'
        )

    return f'<div class="col-card">{header}{stats_row}{detail}</div>'


# ── Public API ────────────────────────────────────────────────────────────────

def profiling_report(
    profile: "DatasetProfile",
    title: str = "Data Profiling Report",
    ai_summary: str = "",
    initial_theme: str = "light",
) -> str:
    """Generate a self-contained HTML profiling report."""
    dataset_name = f"{profile.schema_name}.{profile.table_name}"

    header = (
        f'<header>'
        f'{_THEME_BTN}'
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
    return _html_page(title, body, initial_theme=initial_theme)


def quality_report(
    results: list[dict],
    dataset_name: str = "Dataset",
    title: str = "Data Quality Report",
    ai_summary: str = "",
    initial_theme: str = "light",
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
        f'{_THEME_BTN}'
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
    return _html_page(title, body, initial_theme=initial_theme)


def save_report(html: str, path: str) -> None:
    """Write HTML to file."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
