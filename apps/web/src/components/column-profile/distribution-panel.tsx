"use client";

interface HistBucket {
  lower: number;
  upper: number;
  count: number;
  is_outlier: boolean;
}

interface ColumnStats {
  kind: string;
  p_min: number | null;
  p_max: number | null;
  p_mean: number | null;
  p_stddev: number | null;
  p2: number | null; p5: number | null; p10: number | null;
  p25: number | null; p50: number | null; p75: number | null;
  p90: number | null; p95: number | null; p98: number | null; p99: number | null;
  histogram: HistBucket[];
}

function fmtFloat(v: number | null, d = 4): string {
  if (v === null) return "--";
  if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(2)}M`;
  if (Math.abs(v) >= 1_000) return `${(v / 1_000).toFixed(2)}K`;
  return v.toFixed(d);
}

function Histogram({ buckets }: { buckets: HistBucket[] }) {
  if (!buckets || buckets.length === 0) return null;

  const maxCount = Math.max(...buckets.map(b => b.count), 1);
  const W = 360, H = 120, PL = 8, PB = 20, PT = 8, PR = 8;
  const IW = W - PL - PR;
  const IH = H - PT - PB;
  const bw = IW / buckets.length;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: H, display: "block" }}>
      {/* Baseline */}
      <line x1={PL} y1={H - PB} x2={W - PR} y2={H - PB} stroke="var(--line)" strokeWidth={1} />
      {/* Bars */}
      {buckets.map((b, i) => {
        const barH = (b.count / maxCount) * IH;
        const x = PL + i * bw;
        const y = H - PB - barH;
        const fill = b.is_outlier ? "var(--fail)" : "var(--accent)";
        return (
          <rect key={i} x={x + 0.5} y={y} width={bw - 1} height={barH}
            fill={fill} opacity={b.is_outlier ? 0.6 : 0.75} />
        );
      })}
      {/* X-axis labels: min, mid, max */}
      {buckets.length > 0 && (
        <>
          <text x={PL} y={H - 4} textAnchor="start" fontSize={8} fill="var(--fg-3)" fontFamily="var(--font-jetbrains-mono)">
            {fmtFloat(buckets[0].lower, 2)}
          </text>
          <text x={W / 2} y={H - 4} textAnchor="middle" fontSize={8} fill="var(--fg-3)" fontFamily="var(--font-jetbrains-mono)">
            {fmtFloat((buckets[Math.floor(buckets.length / 2)].lower + buckets[Math.floor(buckets.length / 2)].upper) / 2, 2)}
          </text>
          <text x={W - PR} y={H - 4} textAnchor="end" fontSize={8} fill="var(--fg-3)" fontFamily="var(--font-jetbrains-mono)">
            {fmtFloat(buckets[buckets.length - 1].upper, 2)}
          </text>
        </>
      )}
    </svg>
  );
}

const PERCENTILE_ROWS = [
  { label: "Min", key: "p_min" },
  { label: "p2", key: "p2" },
  { label: "p5", key: "p5" },
  { label: "p10", key: "p10" },
  { label: "p25", key: "p25" },
  { label: "p50 (median)", key: "p50" },
  { label: "Mean", key: "p_mean" },
  { label: "p75", key: "p75" },
  { label: "p90", key: "p90" },
  { label: "p95", key: "p95" },
  { label: "p98", key: "p98" },
  { label: "p99", key: "p99" },
  { label: "Max", key: "p_max" },
  { label: "Std dev", key: "p_stddev" },
] as const;

type PercentileKey = typeof PERCENTILE_ROWS[number]["key"];

export function DistributionPanel({ stats }: { stats: ColumnStats | null }) {
  if (!stats || stats.kind !== "numeric") {
    return (
      <div className="border border-line" style={{ background: "var(--bg-1)" }}>
        <div className="px-4 py-2.5 border-b border-line">
          <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Distribution</span>
        </div>
        <div className="px-4 py-8 t-small flex items-center justify-center" style={{ color: "var(--fg-3)" }}>
          {stats?.kind === "categorical" ? "Categorical column — see Top values" : "No distribution data"}
        </div>
      </div>
    );
  }

  const outlierCount = stats.histogram?.filter(b => b.is_outlier).reduce((s, b) => s + b.count, 0) ?? 0;

  return (
    <div className="border border-line" style={{ background: "var(--bg-1)" }}>
      <div className="px-4 py-2.5 border-b border-line flex items-center justify-between">
        <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Distribution</span>
        {outlierCount > 0 && (
          <span className="t-micro font-mono" style={{ color: "var(--fail)", fontFamily: "var(--font-jetbrains-mono)" }}>
            {outlierCount.toLocaleString()} outliers
          </span>
        )}
      </div>
      <div className="px-4 py-4">
        <div className="flex gap-6 items-start">
          {/* Histogram */}
          <div style={{ flex: "1 1 0", minWidth: 0 }}>
            <p className="t-micro mb-2" style={{ color: "var(--fg-3)", letterSpacing: "0.06em", textTransform: "uppercase" }}>
              Frequency distribution
            </p>
            <Histogram buckets={stats.histogram ?? []} />
            <div className="flex items-center gap-3 mt-2">
              <div className="flex items-center gap-1.5">
                <div style={{ width: 10, height: 8, background: "var(--accent)", opacity: 0.75 }} />
                <span className="t-micro" style={{ color: "var(--fg-3)" }}>normal</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div style={{ width: 10, height: 8, background: "var(--fail)", opacity: 0.6 }} />
                <span className="t-micro" style={{ color: "var(--fg-3)" }}>outlier range</span>
              </div>
            </div>
          </div>

          {/* Percentile table */}
          <div style={{ width: 180, flexShrink: 0 }}>
            <p className="t-micro mb-2" style={{ color: "var(--fg-3)", letterSpacing: "0.06em", textTransform: "uppercase" }}>
              Percentiles
            </p>
            <div className="border border-line" style={{ background: "var(--bg-0)" }}>
              {PERCENTILE_ROWS.map(({ label, key }, i) => {
                const v = stats[key as PercentileKey] as number | null;
                const isMedian = key === "p50";
                const isMean = key === "p_mean";
                return (
                  <div
                    key={key}
                    className="flex items-center justify-between px-3 py-1.5 border-b border-line last:border-0"
                    style={{ background: isMedian || isMean ? "var(--bg-2)" : undefined }}
                  >
                    <span className="t-micro" style={{ color: "var(--fg-3)" }}>{label}</span>
                    <span className="t-micro font-mono" style={{ color: "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)" }}>
                      {fmtFloat(v)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
