"use client";

import { useMemo, useState } from "react";

interface RunPoint {
  id: number;
  detector: string;
  score: number | null;
  verdict: string | null;
  ran_at: string;
}

interface SchemaVersion {
  id: number;
  data_type: string | null;
  nullable: boolean | null;
  position: number | null;
  recorded_at: string;
}

const DETECTOR_CAT: Record<string, string> = {
  completeness: "completeness", null_fraction: "completeness", volume: "completeness",
  volume_anomaly: "completeness", freshness_seconds_behind: "completeness",
  uniqueness: "validity", validity: "validity", set_membership: "validity",
  set_exclusion: "validity", regex_match: "validity", value_in_range: "validity",
  string_length_range: "validity", date_format: "validity", string_case: "validity",
  sql_assertion: "validity", referential_integrity_rate: "validity",
  referential_integrity: "validity", column_pair: "validity", composite_uniqueness: "validity",
  ks_pvalue: "drift", ks_drift: "drift", wasserstein_1: "drift", psi: "drift",
  kl_divergence: "drift", js_divergence: "drift", chi_square_drift: "drift",
  cramers_v: "drift", mmd: "drift", mutual_information: "drift", benford_law_fit: "drift",
  mad_outlier_fraction: "outliers", double_mad_outlier_fraction: "outliers",
  zscore_outlier_fraction: "outliers", adjusted_boxplot_fraction: "outliers",
  iqr_fence: "outliers", grubbs: "outliers", generalized_esd: "outliers",
  stl_residual_zscore: "timeseries", cusum: "timeseries", page_hinkley: "timeseries",
  holt_winters: "timeseries", prophet_anomaly: "timeseries",
};

const CAT_COLOR: Record<string, string> = {
  completeness: "var(--pass)",
  validity: "var(--accent)",
  drift: "var(--warn)",
  outliers: "var(--fail)",
  timeseries: "#9b8fff",
  custom: "var(--fg-3)",
};

function detectorColor(slug: string): string {
  return CAT_COLOR[DETECTOR_CAT[slug] ?? "custom"] ?? "var(--fg-3)";
}

const WINDOWS = [
  { label: "7d", days: 7 },
  { label: "14d", days: 14 },
  { label: "30d", days: 30 },
  { label: "90d", days: 90 },
];

const W = 780, H = 180, PL = 44, PB = 28, PT = 12, PR = 12;
const IW = W - PL - PR;
const IH = H - PT - PB;

export function TimeSeriesPanel({
  history,
  schemaHistory,
}: {
  history: RunPoint[];
  schemaHistory: SchemaVersion[];
}) {
  const [windowDays, setWindowDays] = useState(30);

  const { valid, byDetector, bandPoints, outliers, schemaTimes, tMin, tMax, yMax } = useMemo(() => {
    const cutoff = Date.now() - windowDays * 86_400_000;
    const valid = history
      .filter(r => r.score !== null && new Date(r.ran_at).getTime() >= cutoff)
      .sort((a, b) => new Date(a.ran_at).getTime() - new Date(b.ran_at).getTime());

    if (valid.length === 0) {
      return { valid: [], byDetector: {}, bandPoints: [], outliers: [], schemaTimes: [], tMin: 0, tMax: 0, yMax: 1 };
    }

    const times = valid.map(r => new Date(r.ran_at).getTime());
    const tMin = Math.min(...times);
    const tMax = Math.max(...times);
    const scores = valid.map(r => r.score ?? 0);
    const yMax = Math.max(...scores, 0.1) * 1.15;

    // Group by detector
    const byDetector: Record<string, RunPoint[]> = {};
    for (const r of valid) {
      if (!byDetector[r.detector]) byDetector[r.detector] = [];
      byDetector[r.detector].push(r);
    }

    // Rolling expected band (p25-p75 over all scores sorted by time)
    const WINDOW_SIZE = Math.max(3, Math.floor(valid.length / 6));
    const bandPoints: Array<{ t: number; lo: number; hi: number }> = [];
    for (let i = WINDOW_SIZE; i <= valid.length; i++) {
      const slice = valid.slice(i - WINDOW_SIZE, i).map(r => r.score ?? 0).sort((a, b) => a - b);
      const p25 = slice[Math.floor(slice.length * 0.25)];
      const p75 = slice[Math.floor(slice.length * 0.75)];
      const t = new Date(valid[i - 1].ran_at).getTime();
      bandPoints.push({ t, lo: p25, hi: p75 });
    }

    // Outlier annotations: points > 2σ from mean
    const mean = scores.reduce((s, v) => s + v, 0) / scores.length;
    const stddev = Math.sqrt(scores.reduce((s, v) => s + (v - mean) ** 2, 0) / scores.length);
    const outliers = valid.filter(r => Math.abs((r.score ?? 0) - mean) > 2 * stddev);

    // Schema change times within window
    const schemaTimes = schemaHistory
      .map(s => new Date(s.recorded_at).getTime())
      .filter(t => t >= cutoff);

    return { valid, byDetector, bandPoints, outliers, schemaTimes, tMin, tMax, yMax };
  }, [history, schemaHistory, windowDays]);

  const tRange = Math.max(tMax - tMin, 1);
  const xp = (t: number) => PL + ((t - tMin) / tRange) * IW;
  const yp = (s: number) => PT + (1 - Math.min(s, yMax) / yMax) * IH;

  const yGridVals = [0, 0.25, 0.5, 0.75, 1.0].map(f => f * yMax).filter(v => v <= yMax);
  const xTicks = valid.length > 0
    ? [
        { t: tMin, anchor: "start" as const },
        { t: (tMin + tMax) / 2, anchor: "middle" as const },
        { t: tMax, anchor: "end" as const },
      ]
    : [];

  function fmtDate(t: number) {
    const d = new Date(t);
    return `${d.getMonth() + 1}/${d.getDate()}`;
  }

  const detectors = Object.keys(byDetector);

  // Band area path
  let bandPath = "";
  if (bandPoints.length >= 2) {
    const topPts = bandPoints.map(p => `${xp(p.t).toFixed(1)},${yp(p.hi).toFixed(1)}`).join(" L ");
    const botPts = [...bandPoints].reverse().map(p => `${xp(p.t).toFixed(1)},${yp(p.lo).toFixed(1)}`).join(" L ");
    bandPath = `M ${topPts} L ${botPts} Z`;
  }

  return (
    <div className="border border-line" style={{ background: "var(--bg-1)" }}>
      <div className="px-4 py-2.5 border-b border-line flex items-center justify-between">
        <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
          Check score history
        </span>
        <div className="flex items-center gap-0.5">
          {WINDOWS.map(w => (
            <button
              key={w.days}
              onClick={() => setWindowDays(w.days)}
              className="t-micro px-2 py-0.5 font-mono"
              style={{
                background: windowDays === w.days ? "var(--bg-2)" : "none",
                border: windowDays === w.days ? "1px solid var(--line)" : "1px solid transparent",
                color: windowDays === w.days ? "var(--fg-1)" : "var(--fg-3)",
                cursor: "pointer",
                fontFamily: "var(--font-jetbrains-mono)",
              }}
            >
              {w.label}
            </button>
          ))}
        </div>
      </div>

      {valid.length === 0 ? (
        <div className="px-4 py-8 t-small flex items-center justify-center" style={{ color: "var(--fg-3)" }}>
          No runs in last {windowDays}d
        </div>
      ) : (
        <div className="px-4 py-3">
          <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: H, display: "block" }}>
            {/* Y grid */}
            {yGridVals.map(v => (
              <line key={v} x1={PL} y1={yp(v)} x2={W - PR} y2={yp(v)}
                stroke="var(--line)" strokeWidth={1} opacity={0.7} />
            ))}
            {/* Y labels */}
            {yGridVals.map(v => (
              <text key={v} x={PL - 5} y={yp(v) + 3.5} textAnchor="end"
                fontSize={9} fill="var(--fg-3)" fontFamily="var(--font-jetbrains-mono)">
                {(v * 100).toFixed(0)}%
              </text>
            ))}
            {/* Axes */}
            <line x1={PL} y1={PT} x2={PL} y2={H - PB} stroke="var(--line)" strokeWidth={1} />
            <line x1={PL} y1={H - PB} x2={W - PR} y2={H - PB} stroke="var(--line)" strokeWidth={1} />
            {/* Schema change vertical lines */}
            {schemaTimes.map((t, i) => (
              <line key={i} x1={xp(t)} y1={PT} x2={xp(t)} y2={H - PB}
                stroke="var(--warn)" strokeWidth={1} strokeDasharray="3,3" opacity={0.7} />
            ))}
            {/* Expected band (p25-p75) */}
            {bandPath && (
              <path d={bandPath} fill="var(--accent)" opacity={0.08} />
            )}
            {/* Lines per detector */}
            {Object.entries(byDetector).map(([det, pts]) => {
              const sorted = [...pts].sort((a, b) => new Date(a.ran_at).getTime() - new Date(b.ran_at).getTime());
              const d = sorted.map((p, i) =>
                `${i === 0 ? "M" : "L"} ${xp(new Date(p.ran_at).getTime()).toFixed(1)} ${yp(p.score ?? 0).toFixed(1)}`
              ).join(" ");
              return (
                <path key={det} d={d} fill="none" stroke={detectorColor(det)}
                  strokeWidth={1.5} opacity={0.85} strokeLinejoin="round" />
              );
            })}
            {/* Dots */}
            {valid.map((r, i) => (
              <circle key={i}
                cx={xp(new Date(r.ran_at).getTime())} cy={yp(r.score ?? 0)}
                r={2.5} fill={detectorColor(r.detector)} opacity={0.8} />
            ))}
            {/* Outlier annotations */}
            {outliers.map((r, i) => {
              const cx = xp(new Date(r.ran_at).getTime());
              const cy = yp(r.score ?? 0);
              return (
                <g key={i}>
                  <circle cx={cx} cy={cy} r={4} fill="none"
                    stroke={detectorColor(r.detector)} strokeWidth={1} opacity={0.9} />
                  <text x={cx} y={cy - 7} textAnchor="middle"
                    fontSize={8} fill="var(--fg-3)" fontFamily="var(--font-jetbrains-mono)">
                    2σ
                  </text>
                </g>
              );
            })}
            {/* X labels */}
            {xTicks.map(({ t, anchor }) => (
              <text key={t} x={xp(t)} y={H - 6} textAnchor={anchor}
                fontSize={9} fill="var(--fg-3)" fontFamily="var(--font-jetbrains-mono)">
                {fmtDate(t)}
              </text>
            ))}
          </svg>

          {/* Legend */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1.5 px-1">
            {detectors.map(det => (
              <div key={det} className="flex items-center gap-1.5">
                <div style={{ width: 14, height: 2, background: detectorColor(det) }} />
                <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>{det}</span>
              </div>
            ))}
            {bandPoints.length > 0 && (
              <div className="flex items-center gap-1.5">
                <div style={{ width: 14, height: 8, background: "var(--accent)", opacity: 0.2 }} />
                <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>expected band</span>
              </div>
            )}
            {schemaTimes.length > 0 && (
              <div className="flex items-center gap-1.5">
                <div style={{ width: 14, height: 0, borderTop: "1px dashed var(--warn)" }} />
                <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>schema change</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
