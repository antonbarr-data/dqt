# dqt Public Quality Dashboard

URL: https://dqt.dev/quality (planned)

## What it shows

Per-detector precision, recall, and F1 on three benchmark datasets:
- Synthetic warehouse shapes (lognormal/normal/Poisson/Beta)
- NAB (Numenta Anomaly Benchmark) subset
- Yahoo Webscope S5 subset

Updated on each PyPI release. Source: `examples/benchmarks/results.csv`.

Every detector slug maps to an entry in `docs/algorithms/`. Baselines (`_always_alert`,
`_never_alert`, `_random_50pct`, `_naive_zscore`) are included to make relative
gains legible.

## Static prototype

<details>
<summary>HTML prototype (deploy to GitHub Pages)</summary>

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>dqt Quality Dashboard</title>
  <style>
    :root {
      --bg: #0f1117;
      --bg-1: #181c24;
      --bg-2: #1e232d;
      --line: #2a3040;
      --fg-0: #e8ecf2;
      --fg-1: #9aa5b8;
      --fg-2: #5a6478;
      --accent: #9dd0b0;
      --pass: #7fb394;
      --warn: #d9b566;
      --fail: #e07b6e;
      --mono: "JetBrains Mono", "Fira Code", monospace;
      --sans: "Inter Tight", "Inter", system-ui, sans-serif;
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html { background: var(--bg); color: var(--fg-0); font-family: var(--sans); font-size: 14px; }
    body { max-width: 1100px; margin: 0 auto; padding: 40px 24px 80px; }

    header { border-bottom: 1px solid var(--line); padding-bottom: 24px; margin-bottom: 32px; }
    header h1 {
      font-size: 20px; font-weight: 300; letter-spacing: -0.03em;
      font-family: var(--mono); color: var(--fg-0);
    }
    header h1 span { color: var(--accent); }
    .meta { margin-top: 8px; font-size: 12px; color: var(--fg-2); font-family: var(--mono); }
    .meta a { color: var(--fg-1); text-decoration: none; }
    .meta a:hover { color: var(--accent); }

    .controls {
      display: flex; gap: 12px; align-items: center; margin-bottom: 20px;
      flex-wrap: wrap;
    }
    .controls label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--fg-2); }
    select, input[type="text"] {
      background: var(--bg-1); border: 1px solid var(--line); color: var(--fg-0);
      font-family: var(--mono); font-size: 12px; padding: 5px 10px; outline: none;
    }
    select:focus, input[type="text"]:focus { border-color: var(--accent); }
    .filter-group { display: flex; align-items: center; gap: 6px; }

    .notice {
      background: var(--bg-1); border: 1px solid var(--line); border-left: 3px solid var(--accent);
      padding: 10px 14px; font-size: 12px; color: var(--fg-1); margin-bottom: 24px;
      font-family: var(--mono);
    }

    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    thead tr { border-bottom: 1px solid var(--line); }
    th {
      text-align: left; padding: 8px 12px; font-size: 10px; font-weight: 500;
      text-transform: uppercase; letter-spacing: 0.12em; color: var(--fg-2);
      font-family: var(--mono); cursor: pointer; user-select: none;
      white-space: nowrap;
    }
    th:hover { color: var(--fg-0); }
    th.sorted { color: var(--accent); }
    th.sorted::after { content: " v"; font-size: 9px; }
    th.sorted.asc::after { content: " ^"; font-size: 9px; }
    th.num { text-align: right; }

    tbody tr { border-bottom: 1px solid var(--line); }
    tbody tr:hover { background: var(--bg-1); }
    tbody tr.baseline { opacity: 0.5; }
    td { padding: 8px 12px; vertical-align: middle; }
    td.mono { font-family: var(--mono); font-size: 12px; }
    td.num { text-align: right; font-family: var(--mono); font-size: 12px; }

    .slug-link { color: var(--fg-1); text-decoration: none; }
    .slug-link:hover { color: var(--accent); }

    .family-badge {
      display: inline-block; font-family: var(--mono); font-size: 10px;
      padding: 2px 6px; border: 1px solid var(--line); color: var(--fg-2);
      text-transform: uppercase; letter-spacing: 0.08em;
    }
    .family-drift    { border-color: #3a5a8a; color: #7aa8d8; }
    .family-outlier  { border-color: #5a3a6a; color: #b87ad8; }
    .family-timeseries { border-color: #2a5a4a; color: #7ad8b8; }
    .family-distribution { border-color: #5a4a2a; color: #d8b87a; }
    .family-baseline { border-color: var(--line); color: var(--fg-2); }

    .bar-cell { width: 140px; }
    .bar-wrap { display: flex; align-items: center; gap: 8px; }
    .bar-track {
      flex: 1; height: 4px; background: var(--bg-2); position: relative; overflow: hidden;
    }
    .bar-fill { height: 100%; transition: width 0.24s ease-out; }
    .bar-label { font-family: var(--mono); font-size: 12px; min-width: 36px; text-align: right; }

    .ci { font-size: 10px; color: var(--fg-2); font-family: var(--mono); }

    .summary-band {
      display: flex; gap: 24px; margin-bottom: 28px; flex-wrap: wrap;
    }
    .kpi-card {
      background: var(--bg-1); border: 1px solid var(--line); padding: 14px 18px;
      min-width: 140px;
    }
    .kpi-label {
      font-size: 10px; text-transform: uppercase; letter-spacing: 0.16em;
      color: var(--fg-2); font-family: var(--mono); margin-bottom: 6px;
    }
    .kpi-value {
      font-size: 28px; font-weight: 300; letter-spacing: -0.02em;
      font-family: var(--mono); color: var(--fg-0); font-variant-numeric: tabular-nums;
    }
    .kpi-value.pass { color: var(--pass); }
    .kpi-value.warn { color: var(--warn); }

    footer {
      margin-top: 48px; border-top: 1px solid var(--line); padding-top: 20px;
      font-size: 11px; color: var(--fg-2); font-family: var(--mono);
    }
    footer a { color: var(--fg-1); text-decoration: none; }
    footer a:hover { color: var(--accent); }
  </style>
</head>
<body>

<header>
  <h1><span>dqt</span> / quality</h1>
  <p class="meta">
    v0.1.0 &nbsp;&middot;&nbsp; released 2026-05-13 &nbsp;&middot;&nbsp;
    <a href="https://github.com/dqt-dev/dqt/blob/main/examples/benchmarks/results.csv">results.csv</a>
    &nbsp;&middot;&nbsp;
    <a href="https://github.com/dqt-dev/dqt/blob/main/examples/benchmarks/detector_benchmark.ipynb">benchmark notebook</a>
    &nbsp;&middot;&nbsp;
    <a href="https://dqt.dev/docs/algorithms/">algorithm docs</a>
  </p>
</header>

<div class="notice">
  Updated automatically on each PyPI release by the CI benchmark job.
  Every row is 30 independent trials on held-out data.
  95% bootstrap confidence intervals shown.
</div>

<div class="summary-band" id="summary-band"></div>

<div class="controls">
  <div class="filter-group">
    <label>family</label>
    <select id="family-filter">
      <option value="">all</option>
      <option value="drift">drift</option>
      <option value="outlier">outlier</option>
      <option value="timeseries">timeseries</option>
      <option value="distribution">distribution</option>
      <option value="baseline">baseline</option>
    </select>
  </div>
  <div class="filter-group">
    <label>search</label>
    <input type="text" id="search-filter" placeholder="detector slug..." style="width:200px" />
  </div>
  <div class="filter-group">
    <label>
      <input type="checkbox" id="hide-baselines" checked />
      hide baselines
    </label>
  </div>
</div>

<table id="results-table">
  <thead>
    <tr>
      <th data-col="slug">Detector</th>
      <th data-col="family">Family</th>
      <th data-col="f1_mean" class="num sorted">F1</th>
      <th data-col="precision_mean" class="num">Precision</th>
      <th data-col="recall_mean" class="num">Recall</th>
      <th data-col="fpr_mean" class="num">FPR</th>
      <th class="bar-cell">F1 bar</th>
    </tr>
  </thead>
  <tbody id="table-body"></tbody>
</table>

<footer>
  Benchmark: synthetic warehouse shapes (lognormal / normal / Poisson / Beta), NAB subset, Yahoo Webscope S5 subset.
  FPR = false-positive rate.
  Source code: <a href="https://github.com/dqt-dev/dqt/tree/main/examples/benchmarks">examples/benchmarks/</a>.
  License: MIT.
</footer>

<script>
const RAW = [
  {slug:"_always_alert",family:"baseline",n:30,f1:0.667,f1_lo:0.667,f1_hi:0.667,precision:0.500,recall:1.000,fpr:1.000},
  {slug:"_never_alert",family:"baseline",n:30,f1:0.000,f1_lo:0.000,f1_hi:0.000,precision:null,recall:0.000,fpr:0.000},
  {slug:"_random_50pct",family:"baseline",n:30,f1:0.486,f1_lo:0.421,f1_hi:0.550,precision:0.485,recall:0.500,fpr:0.508},
  {slug:"_naive_zscore",family:"baseline",n:30,f1:0.141,f1_lo:0.102,f1_hi:0.180,precision:1.000,recall:0.079,fpr:0.000},
  {slug:"adjusted_boxplot_fraction",family:"outlier",n:30,f1:0.860,f1_lo:0.842,f1_hi:0.879,precision:1.000,recall:0.758,fpr:0.000},
  {slug:"auto_outlier",family:"outlier",n:30,f1:0.926,f1_lo:0.917,f1_hi:0.934,precision:1.000,recall:0.863,fpr:0.000},
  {slug:"benford_law_fit",family:"distribution",n:30,f1:0.667,f1_lo:0.667,f1_hi:0.667,precision:0.500,recall:1.000,fpr:1.000},
  {slug:"cusum",family:"timeseries",n:30,f1:0.884,f1_lo:0.868,f1_hi:0.899,precision:0.990,recall:0.800,fpr:0.008},
  {slug:"double_mad_outlier_fraction",family:"outlier",n:30,f1:0.536,f1_lo:0.523,f1_hi:0.549,precision:1.000,recall:0.367,fpr:0.000},
  {slug:"generalized_esd",family:"outlier",n:30,f1:0.398,f1_lo:0.375,f1_hi:0.420,precision:0.958,recall:0.254,fpr:0.017},
  {slug:"grubbs",family:"outlier",n:30,f1:0.526,f1_lo:0.498,f1_hi:0.554,precision:0.711,recall:0.421,fpr:0.179},
  {slug:"holt_winters",family:"timeseries",n:30,f1:0.933,f1_lo:0.933,f1_hi:0.933,precision:1.000,recall:0.875,fpr:0.000},
  {slug:"iqr_fence",family:"outlier",n:30,f1:0.841,f1_lo:0.828,f1_hi:0.854,precision:0.980,recall:0.738,fpr:0.017},
  {slug:"js_divergence",family:"drift",n:30,f1:0.778,f1_lo:0.768,f1_hi:0.788,precision:1.000,recall:0.637,fpr:0.000},
  {slug:"kl_divergence",family:"drift",n:30,f1:0.769,f1_lo:0.769,f1_hi:0.769,precision:1.000,recall:0.625,fpr:0.000},
  {slug:"ks_pvalue",family:"drift",n:30,f1:0.920,f1_lo:0.908,f1_hi:0.932,precision:0.968,recall:0.879,fpr:0.033},
  {slug:"mad_outlier_fraction",family:"outlier",n:30,f1:0.222,f1_lo:0.222,f1_hi:0.222,precision:1.000,recall:0.125,fpr:0.000},
  {slug:"mmd",family:"drift",n:30,f1:0.708,f1_lo:0.689,f1_hi:0.726,precision:1.000,recall:0.550,fpr:0.000},
  {slug:"monotonicity",family:"timeseries",n:30,f1:0.667,f1_lo:0.667,f1_hi:0.667,precision:0.500,recall:1.000,fpr:1.000},
  {slug:"page_hinkley",family:"timeseries",n:30,f1:0.776,f1_lo:0.744,f1_hi:0.807,precision:0.771,recall:0.792,fpr:0.254},
  {slug:"psi",family:"drift",n:30,f1:0.775,f1_lo:0.767,f1_hi:0.783,precision:1.000,recall:0.633,fpr:0.000},
  {slug:"stl_residual_zscore",family:"timeseries",n:30,f1:0.545,f1_lo:0.545,f1_hi:0.545,precision:0.429,recall:0.750,fpr:1.000},
  {slug:"wasserstein_1",family:"drift",n:30,f1:0.933,f1_lo:0.933,f1_hi:0.933,precision:1.000,recall:0.875,fpr:0.000},
  {slug:"zscore_outlier_fraction",family:"outlier",n:30,f1:0.877,f1_lo:0.873,f1_hi:0.881,precision:0.879,recall:0.875,fpr:0.121},
];

const fmt = v => v == null ? "-" : v.toFixed(3);
const pct = v => v == null ? 0 : Math.round(v * 100);

function barColor(v) {
  if (v == null) return "#2a3040";
  if (v >= 0.85) return "#7fb394";
  if (v >= 0.70) return "#d9b566";
  return "#e07b6e";
}

let sortCol = "f1_mean";
let sortAsc = false;
let colKey = "";
let searchQ = "";
let hideBaselines = true;

function colMap(col) {
  return {f1_mean:"f1", precision_mean:"precision", recall_mean:"recall",
          fpr_mean:"fpr", slug:"slug", family:"family"}[col] || col;
}

function getSortVal(row, col) {
  const k = colMap(col);
  return row[k] == null ? -Infinity : row[k];
}

function buildSummary(data) {
  const non = data.filter(r => !r.slug.startsWith("_"));
  const best = non.reduce((a,b) => b.f1 > a.f1 ? b : a, non[0]);
  const avgF1 = (non.reduce((s,r) => s + r.f1, 0) / non.length);
  const avgPrec = (non.reduce((s,r) => s + (r.precision||0), 0) / non.length);

  const kpis = [
    {label:"detectors", value: non.length, cls:""},
    {label:"best f1", value: best.f1.toFixed(3) + " (" + best.slug + ")", cls: best.f1 >= 0.9 ? "pass" : "warn"},
    {label:"avg f1", value: avgF1.toFixed(3), cls: avgF1 >= 0.75 ? "pass" : "warn"},
    {label:"avg precision", value: avgPrec.toFixed(3), cls: avgPrec >= 0.85 ? "pass" : "warn"},
  ];
  document.getElementById("summary-band").innerHTML = kpis.map(k =>
    `<div class="kpi-card"><div class="kpi-label">${k.label}</div><div class="kpi-value ${k.cls}">${k.value}</div></div>`
  ).join("");
}

function render() {
  let rows = [...RAW];
  if (hideBaselines) rows = rows.filter(r => !r.slug.startsWith("_"));
  if (colKey) rows = rows.filter(r => r.family === colKey);
  if (searchQ) rows = rows.filter(r => r.slug.includes(searchQ));
  rows.sort((a, b) => {
    const av = getSortVal(a, sortCol), bv = getSortVal(b, sortCol);
    return sortAsc ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1);
  });

  buildSummary(RAW);

  document.getElementById("table-body").innerHTML = rows.map(r => {
    const isBase = r.slug.startsWith("_");
    return `<tr class="${isBase ? "baseline" : ""}">
      <td class="mono"><a class="slug-link" href="https://dqt.dev/docs/algorithms/${r.slug}">${r.slug}</a></td>
      <td><span class="family-badge family-${r.family}">${r.family}</span></td>
      <td class="num">${fmt(r.f1)}<br><span class="ci">[${fmt(r.f1_lo)}, ${fmt(r.f1_hi)}]</span></td>
      <td class="num">${fmt(r.precision)}</td>
      <td class="num">${fmt(r.recall)}</td>
      <td class="num">${fmt(r.fpr)}</td>
      <td class="bar-cell">
        <div class="bar-wrap">
          <div class="bar-track"><div class="bar-fill" style="width:${pct(r.f1)}%;background:${barColor(r.f1)}"></div></div>
          <span class="bar-label" style="color:${barColor(r.f1)}">${pct(r.f1)}%</span>
        </div>
      </td>
    </tr>`;
  }).join("");

  document.querySelectorAll("th[data-col]").forEach(th => {
    th.classList.remove("sorted","asc");
    if (th.dataset.col === sortCol) {
      th.classList.add("sorted");
      if (sortAsc) th.classList.add("asc");
    }
  });
}

document.querySelectorAll("th[data-col]").forEach(th => {
  th.addEventListener("click", () => {
    if (sortCol === th.dataset.col) sortAsc = !sortAsc;
    else { sortCol = th.dataset.col; sortAsc = false; }
    render();
  });
});
document.getElementById("family-filter").addEventListener("change", e => { colKey = e.target.value; render(); });
document.getElementById("search-filter").addEventListener("input", e => { searchQ = e.target.value.trim(); render(); });
document.getElementById("hide-baselines").addEventListener("change", e => { hideBaselines = e.target.checked; render(); });

render();
</script>
</body>
</html>
```

</details>

## How to update

After each release, run `python examples/benchmarks/run_benchmarks.py` and commit
the updated `results.csv`. The CI workflow auto-deploys the updated page.

The CI job (`.github/workflows/benchmark.yml`) runs on every tag matching `dqt-v*`,
writes `results.csv`, regenerates this prototype's inline data block, and publishes
to GitHub Pages via `peaceiris/actions-gh-pages`.

## Interpreting the metrics

- **F1**: harmonic mean of precision and recall. Primary ranking metric.
- **Precision**: fraction of fired alerts that were true anomalies. High precision = low alert fatigue.
- **Recall**: fraction of true anomalies caught. High recall = low missed detection rate.
- **FPR**: false-positive rate on clean windows. Should be near 0 for production use.
- **95% CI**: bootstrap confidence interval over 30 independent trials. Wide CI means the detector is sensitive to random seed or sample draw.

Baselines (`_always_alert`, `_never_alert`, `_random_50pct`, `_naive_zscore`) are
shown grayed-out to anchor interpretation. Any real detector should beat `_naive_zscore`
on F1; most should beat `_random_50pct` on precision.
