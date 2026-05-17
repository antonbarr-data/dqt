import Link from "next/link";
import { notFound } from "next/navigation";
import dynamic from "next/dynamic";
import { serverFetch } from "@/lib/server-api";

const SuggestPanel = dynamic(
  () =>
    import("@/components/checks/suggest-panel").then((m) => m.SuggestPanel),
  {
    ssr: false,
    loading: () => (
      <div className="px-4 py-3 t-small" style={{ color: "var(--fg-3)" }}>
        Loading...
      </div>
    ),
  }
)

interface CheckResult {
  id: number;
  dataset_id: string;
  column: string | null;
  detector: string;
  score: number | null;
  verdict: string | null;
  message: string | null;
  details: Record<string, unknown> | null;
  ran_at_ago: string;
}

interface DatasetDetail {
  id: string;
  source: string;
  schema: string;
  row_count: number | null;
  column_count: number | null;
  check_count: number;
  status: string;
  last_run: string;
  checks: CheckResult[];
}

interface IncidentRow {
  id: number;
  dataset_id: string;
  column: string | null;
  detector: string;
  severity: string;
  message: string;
  status: string;
  opened_ago: string;
}

interface NumericBucket {
  lower: number;
  upper: number;
  count: number;
  is_outlier: boolean;
}

interface NumericStats {
  min: number;
  max: number;
  mean: number;
  stddev: number;
  p25: number;
  p50: number;
  p75: number;
  outlier_lower: number;
  outlier_upper: number;
  total_count: number;
  outlier_low_count: number;
  outlier_high_count: number;
}

interface ColumnProfile {
  kind: "numeric" | "categorical" | "unknown" | "error";
  column: string;
  data_type?: string;
  stats?: NumericStats;
  buckets?: NumericBucket[];
  top_values?: Array<{ value: string; count: number }>;
  other_count?: number;
  total_count?: number;
  error?: string;
}

function VerdictBadge({ verdict }: { verdict: string }) {
  const map: Record<string, { bg: string; color: string }> = {
    pass: { bg: "rgba(127,179,148,0.12)", color: "var(--pass)" },
    warn: { bg: "rgba(217,181,102,0.12)", color: "var(--warn)" },
    fail: { bg: "var(--fail-bg)", color: "var(--fail)" },
  };
  const s = map[verdict] ?? { bg: "var(--bg-2)", color: "var(--fg-3)" };
  return (
    <span
      className="t-micro px-2 py-0.5"
      style={{ background: s.bg, color: s.color, fontFamily: "var(--font-jetbrains-mono)", letterSpacing: "0.04em" }}
    >
      {verdict.toUpperCase()}
    </span>
  );
}

function ScoreGauge({ score, warn, fail }: { score: number; warn: number; fail: number }) {
  const pct = Math.min(score * 100, 100);
  const color = pct >= fail ? "var(--fail)" : pct >= warn ? "var(--warn)" : "var(--pass)";
  return (
    <div style={{ position: "relative", height: 6, background: "var(--bg-3)", width: "100%" }}>
      <div style={{ position: "absolute", top: 0, left: 0, height: "100%", width: `${pct}%`, background: color, transition: "width 600ms ease" }} />
      <div style={{ position: "absolute", top: -2, bottom: -2, left: `${warn}%`, width: 1, background: "var(--warn)", opacity: 0.7 }} />
      <div style={{ position: "absolute", top: -2, bottom: -2, left: `${fail}%`, width: 1, background: "var(--fail)", opacity: 0.7 }} />
    </div>
  );
}

function NullBar({ nullFrac, rows }: { nullFrac: number; rows: number | null }) {
  const nonNullFrac = 1 - nullFrac;
  const nullPct = (nullFrac * 100).toFixed(1);
  const nonNullPct = (nonNullFrac * 100).toFixed(1);
  const nullCount = rows ? Math.round(rows * nullFrac) : null;
  const nonNullCount = rows ? Math.round(rows * nonNullFrac) : null;

  return (
    <div>
      <div style={{ height: 28, display: "flex", width: "100%", gap: 1 }}>
        <div style={{ width: `${nonNullFrac * 100}%`, background: "var(--pass)", opacity: 0.7, display: "flex", alignItems: "center", justifyContent: "center" }}>
          {nonNullFrac > 0.15 && (
            <span style={{ color: "#fff", fontSize: 10, fontFamily: "var(--font-jetbrains-mono)", fontWeight: 500 }}>{nonNullPct}%</span>
          )}
        </div>
        {nullFrac > 0 && (
          <div style={{ width: `${nullFrac * 100}%`, background: nullFrac >= 0.1 ? "var(--fail)" : nullFrac >= 0.02 ? "var(--warn)" : "var(--pass)", opacity: 0.8, display: "flex", alignItems: "center", justifyContent: "center" }}>
            {nullFrac > 0.08 && (
              <span style={{ color: "#fff", fontSize: 10, fontFamily: "var(--font-jetbrains-mono)", fontWeight: 500 }}>{nullPct}%</span>
            )}
          </div>
        )}
      </div>
      <div className="flex items-center gap-6 mt-3">
        <div className="flex items-center gap-2">
          <div style={{ width: 10, height: 10, background: "var(--pass)", opacity: 0.7 }} />
          <span className="t-micro font-mono" style={{ color: "var(--fg-2)" }}>
            non-null {nonNullCount !== null ? `(${nonNullCount.toLocaleString()})` : `${nonNullPct}%`}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div style={{ width: 10, height: 10, background: nullFrac >= 0.02 ? "var(--warn)" : "var(--pass)", opacity: 0.8 }} />
          <span className="t-micro font-mono" style={{ color: "var(--fg-2)" }}>
            null {nullCount !== null ? `(${nullCount.toLocaleString()})` : `${nullPct}%`}
          </span>
        </div>
      </div>
    </div>
  );
}

function fmtV(v: number): string {
  if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (Math.abs(v) >= 1_000) return `${(v / 1_000).toFixed(0)}K`;
  if (Math.abs(v) >= 1) return v.toFixed(1);
  return v.toFixed(3);
}

function ValueHistogram({ buckets, stats }: { buckets: NumericBucket[]; stats: NumericStats }) {
  const W = 560;
  const BAR_H = 90;
  const AXIS_H = 28;
  const TOTAL_H = BAR_H + AXIS_H;

  const n = buckets.length;
  if (n === 0) return null;

  const maxCount = Math.max(...buckets.map(b => b.count), 1);
  const barW = W / n;

  const lo = buckets[0].lower;
  const hi = buckets[n - 1].upper;
  const range = hi - lo || 1;
  const xp = (v: number) => Math.max(0, Math.min(W, ((v - lo) / range) * W));
  const bh = (count: number) => (count / maxCount) * BAR_H;

  const hasOutlierBins = buckets.some(b => b.is_outlier && b.count > 0);
  const totalOutsideRange = stats.outlier_low_count + stats.outlier_high_count;

  // Build x-axis tick positions (avoid overlap: only show if far enough apart)
  const axisTicks: Array<{ v: number; label: string; anchor: "start" | "middle" | "end" }> = [
    { v: lo, label: fmtV(lo), anchor: "start" },
    { v: stats.p25, label: fmtV(stats.p25), anchor: "middle" },
    { v: stats.p50, label: fmtV(stats.p50), anchor: "middle" },
    { v: stats.p75, label: fmtV(stats.p75), anchor: "middle" },
    { v: hi, label: fmtV(hi), anchor: "end" },
  ];

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${TOTAL_H}`} style={{ width: "100%", height: TOTAL_H, display: "block" }}>
        {/* IQR shaded band (Q1-Q3) */}
        <rect
          x={xp(Math.max(lo, stats.p25))}
          y={0}
          width={Math.max(0, xp(Math.min(hi, stats.p75)) - xp(Math.max(lo, stats.p25)))}
          height={BAR_H}
          fill="var(--accent)"
          opacity={0.07}
        />

        {/* Outlier fence dashed lines */}
        {stats.outlier_lower > lo && stats.outlier_lower < hi && (
          <line x1={xp(stats.outlier_lower)} y1={0} x2={xp(stats.outlier_lower)} y2={BAR_H}
            stroke="var(--warn)" strokeWidth={1} strokeDasharray="3,3" opacity={0.45} />
        )}
        {stats.outlier_upper > lo && stats.outlier_upper < hi && (
          <line x1={xp(stats.outlier_upper)} y1={0} x2={xp(stats.outlier_upper)} y2={BAR_H}
            stroke="var(--warn)" strokeWidth={1} strokeDasharray="3,3" opacity={0.45} />
        )}

        {/* Bars */}
        {buckets.map((b, i) => {
          if (b.count === 0) return null;
          const h = bh(b.count);
          return (
            <rect
              key={i}
              x={i * barW}
              y={BAR_H - h}
              width={Math.max(barW - 1, 0.5)}
              height={h}
              fill={b.is_outlier ? "var(--warn)" : "var(--accent)"}
              opacity={b.is_outlier ? 0.72 : 0.58}
            />
          );
        })}

        {/* Median line */}
        {stats.p50 >= lo && stats.p50 <= hi && (
          <line x1={xp(stats.p50)} y1={0} x2={xp(stats.p50)} y2={BAR_H}
            stroke="var(--fg-1)" strokeWidth={1} strokeDasharray="4,3" opacity={0.75} />
        )}
        {/* Mean line */}
        {stats.mean >= lo && stats.mean <= hi && (
          <line x1={xp(stats.mean)} y1={0} x2={xp(stats.mean)} y2={BAR_H}
            stroke="var(--fg-0)" strokeWidth={1} opacity={0.4} />
        )}

        {/* Mean label */}
        {stats.mean >= lo && stats.mean <= hi && (
          <text x={xp(stats.mean)} y={BAR_H - 5} textAnchor="middle" fontSize={9}
            fill="var(--fg-0)" fontFamily="var(--font-jetbrains-mono)" opacity={0.6}>
            mean
          </text>
        )}

        {/* Baseline */}
        <line x1={0} y1={BAR_H} x2={W} y2={BAR_H} stroke="var(--line)" strokeWidth={1} />

        {/* X-axis labels */}
        {axisTicks.map(({ v, label, anchor }) => (
          <text key={label} x={xp(v)} y={BAR_H + 14} textAnchor={anchor}
            fontSize={9} fill="var(--fg-3)" fontFamily="var(--font-jetbrains-mono)">
            {label}
          </text>
        ))}

        {/* Outlier count callouts at edges */}
        {stats.outlier_low_count > 0 && (
          <text x={2} y={BAR_H - 5} fontSize={9} fill="var(--warn)"
            fontFamily="var(--font-jetbrains-mono)">
            {stats.outlier_low_count.toLocaleString()} below
          </text>
        )}
        {stats.outlier_high_count > 0 && (
          <text x={W - 2} y={BAR_H - 5} textAnchor="end" fontSize={9} fill="var(--warn)"
            fontFamily="var(--font-jetbrains-mono)">
            {stats.outlier_high_count.toLocaleString()} above
          </text>
        )}
      </svg>

      {/* Legend + stats row */}
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1 mt-2 px-0.5">
        <div className="flex items-center gap-1.5">
          <div style={{ width: 10, height: 10, background: "var(--accent)", opacity: 0.58 }} />
          <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>within IQR fence</span>
        </div>
        {hasOutlierBins && (
          <div className="flex items-center gap-1.5">
            <div style={{ width: 10, height: 10, background: "var(--warn)", opacity: 0.72 }} />
            <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>outside IQR fence</span>
          </div>
        )}
        <div className="flex items-center gap-1.5">
          <div style={{ width: 14, height: 1, background: "var(--fg-1)", opacity: 0.75 }} />
          <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>median</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div style={{ width: 14, height: 1, background: "var(--fg-0)", opacity: 0.4 }} />
          <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>mean</span>
        </div>
        {totalOutsideRange > 0 && (
          <span className="t-micro font-mono" style={{ color: "var(--warn)" }}>
            {totalOutsideRange.toLocaleString()} values outside p2-p98 range
          </span>
        )}
      </div>

      {/* Statistics summary */}
      <div className="flex flex-wrap gap-x-5 gap-y-1 mt-3 pt-3 border-t border-line px-0.5">
        {[
          ["min", fmtV(stats.min)],
          ["Q1", fmtV(stats.p25)],
          ["median", fmtV(stats.p50)],
          ["mean", fmtV(stats.mean)],
          ["Q3", fmtV(stats.p75)],
          ["max", fmtV(stats.max)],
          ["σ", fmtV(stats.stddev)],
        ].map(([label, value]) => (
          <div key={label} className="flex items-baseline gap-1">
            <span className="t-micro" style={{ color: "var(--fg-3)" }}>{label}</span>
            <span className="t-micro font-mono" style={{ color: "var(--fg-1)" }}>{value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function TopNChart({ topValues, otherCount, totalCount }: {
  topValues: Array<{ value: string; count: number }>;
  otherCount: number;
  totalCount: number;
}) {
  const maxCount = Math.max(...topValues.map(v => v.count), 1);
  return (
    <div className="space-y-1.5">
      {topValues.map(({ value, count }) => {
        const pct = totalCount > 0 ? (count / totalCount * 100).toFixed(1) : "0.0";
        const barW = (count / maxCount * 100).toFixed(1);
        return (
          <div key={value} className="flex items-center gap-2">
            <span className="t-micro font-mono truncate" style={{ color: "var(--fg-1)", width: 130, flexShrink: 0 }} title={value}>
              {value}
            </span>
            <div style={{ flex: 1, height: 12, background: "var(--bg-3)" }}>
              <div style={{ height: "100%", width: `${barW}%`, background: "var(--accent)", opacity: 0.6 }} />
            </div>
            <span className="t-micro font-mono" style={{ color: "var(--fg-3)", width: 70, flexShrink: 0, textAlign: "right" }}>
              {count.toLocaleString()} ({pct}%)
            </span>
          </div>
        );
      })}
      {otherCount > 0 && (
        <div className="flex items-center gap-2">
          <span className="t-micro font-mono" style={{ color: "var(--fg-3)", width: 130, flexShrink: 0 }}>(other)</span>
          <div style={{ flex: 1, height: 12, background: "var(--bg-3)" }}>
            <div style={{ height: "100%", width: `${(otherCount / maxCount * 100).toFixed(1)}%`, background: "var(--bg-3)", opacity: 0.3 }} />
          </div>
          <span className="t-micro font-mono" style={{ color: "var(--fg-3)", width: 70, flexShrink: 0, textAlign: "right" }}>
            {otherCount.toLocaleString()}
          </span>
        </div>
      )}
    </div>
  );
}

export default async function ColumnProfilePage({
  params,
}: {
  params: Promise<{ id: string; column: string }>;
}) {
  const { id, column: rawColumn } = await params;
  const column = decodeURIComponent(rawColumn);

  const [dataset, incidents, profile] = await Promise.all([
    serverFetch<DatasetDetail>(`/datasets/${encodeURIComponent(id)}`, 30),
    serverFetch<IncidentRow[]>(`/incidents?status=open`, 30),
    serverFetch<ColumnProfile>(`/datasets/${encodeURIComponent(id)}/columns/${encodeURIComponent(column)}/profile`, 120),
  ]);

  if (!dataset) notFound();

  const checks = dataset.checks.filter((c) => c.column === column);
  if (checks.length === 0) notFound();

  const check = checks[0];
  const nullFrac = check.score ?? 0;
  const details = check.details ?? {};
  const nullCount = (details.null_count as number) ?? Math.round(nullFrac * (dataset.row_count ?? 0));
  const totalCount = (details.total_count as number) ?? dataset.row_count ?? 0;
  const verdict = check.verdict ?? "unknown";

  const WARN_THRESHOLD = 2;
  const FAIL_THRESHOLD = 10;

  const columnIncidents = (incidents ?? []).filter(
    (i) => i.dataset_id === id && i.column === column
  );

  const yamlDef = `check: null_fraction
dataset: ${id}
column: ${column}
threshold:
  warn: 0.02
  fail: 0.10
baseline: 14d`;

  return (
    <div className="p-6 fade-in">
      {/* breadcrumb */}
      <div className="flex items-center gap-2 mb-6">
        <Link href={"/datasets" as never} className="flex items-center gap-1.5 t-small hover:opacity-80 transition-colors" style={{ color: "var(--accent)", fontFamily: "var(--font-jetbrains-mono)" }}>
          <span style={{ fontSize: 14, lineHeight: 1 }}>←</span>
          <span>Datasets</span>
        </Link>
        <span style={{ color: "var(--fg-3)", fontSize: 12 }}>/</span>
        <Link href={`/datasets/${id}` as never} className="t-small font-mono hover:opacity-80 transition-colors" style={{ color: "var(--accent)" }}>
          {id}
        </Link>
        <span style={{ color: "var(--fg-3)", fontSize: 12 }}>/</span>
        <span className="t-small font-mono" style={{ color: "var(--fg-2)" }}>{column}</span>
      </div>

      {/* header */}
      <div className="flex items-start gap-4 mb-8">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <VerdictBadge verdict={verdict} />
            <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>{check.detector}</span>
          </div>
          <h1 className="font-mono mb-1" style={{ fontSize: 26, fontWeight: 300, color: "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)", letterSpacing: "-0.02em" }}>
            {id}<span style={{ color: "var(--fg-3)" }}>.</span>{column}
          </h1>
          {check.message && (
            <p className="t-small mt-1" style={{ color: "var(--fg-2)" }}>{check.message}</p>
          )}
        </div>
      </div>

      {/* KPI band */}
      <div className="grid grid-cols-4 gap-px border border-line mb-8" style={{ background: "var(--line)" }}>
        {[
          { label: "Null rate", value: `${(nullFrac * 100).toFixed(2)}%`, color: verdict === "fail" ? "var(--fail)" : verdict === "warn" ? "var(--warn)" : "var(--pass)" },
          { label: "Null / Total", value: `${nullCount.toLocaleString()} / ${totalCount.toLocaleString()}`, color: "var(--fg-0)" },
          { label: "Dataset rows", value: dataset.row_count ? dataset.row_count.toLocaleString() : "--", color: "var(--fg-0)" },
          { label: "Last checked", value: check.ran_at_ago, color: "var(--fg-0)" },
        ].map((k) => (
          <div key={k.label} className="px-5 py-4" style={{ background: "var(--bg-1)" }}>
            <p className="kpi-label mb-2" style={{ color: "var(--fg-2)" }}>{k.label}</p>
            <p className="font-mono" style={{ fontSize: 22, fontWeight: 300, color: k.color, fontFamily: "var(--font-jetbrains-mono)", lineHeight: 1.2 }}>
              {k.value}
            </p>
          </div>
        ))}
      </div>

      <div className="flex gap-6" style={{ alignItems: "flex-start" }}>
        {/* left column */}
        <div className="flex-1 min-w-0 space-y-5">

          {/* value distribution (numeric) */}
          {profile?.kind === "numeric" && profile.buckets && profile.stats && profile.buckets.length > 0 && (
            <div className="border border-line" style={{ background: "var(--bg-1)" }}>
              <div className="px-4 py-3 border-b border-line flex items-center justify-between">
                <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                  Value distribution
                </span>
                <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>
                  {profile.stats.total_count.toLocaleString()} non-null · {profile.data_type}
                </span>
              </div>
              <div className="px-4 pt-4 pb-4">
                <ValueHistogram buckets={profile.buckets} stats={profile.stats} />
              </div>
            </div>
          )}

          {/* value distribution (categorical) */}
          {profile?.kind === "categorical" && profile.top_values && profile.top_values.length > 0 && (
            <div className="border border-line" style={{ background: "var(--bg-1)" }}>
              <div className="px-4 py-3 border-b border-line flex items-center justify-between">
                <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                  Top values
                </span>
                <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>
                  {profile.total_count?.toLocaleString()} non-null · {profile.data_type}
                </span>
              </div>
              <div className="px-4 py-4">
                <TopNChart
                  topValues={profile.top_values}
                  otherCount={profile.other_count ?? 0}
                  totalCount={profile.total_count ?? 0}
                />
              </div>
            </div>
          )}

          {/* null distribution */}
          <div className="border border-line" style={{ background: "var(--bg-1)" }}>
            <div className="px-4 py-3 border-b border-line flex items-center justify-between">
              <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                Null distribution
              </span>
              <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>baseline 14d</span>
            </div>
            <div className="p-6">
              <NullBar nullFrac={nullFrac} rows={dataset.row_count} />
            </div>
          </div>

          {/* statistical evidence */}
          <div className="border border-line" style={{ background: "var(--bg-1)" }}>
            <div className="px-4 py-3 border-b border-line t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
              Statistical evidence
            </div>
            <div className="p-4 space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="t-small" style={{ color: "var(--fg-1)" }}>Null fraction</span>
                  <div className="flex items-center gap-3">
                    <span className="t-small font-mono" style={{ color: verdict === "fail" ? "var(--fail)" : verdict === "warn" ? "var(--warn)" : "var(--pass)" }}>
                      {(nullFrac * 100).toFixed(3)}%
                    </span>
                    <VerdictBadge verdict={verdict} />
                  </div>
                </div>
                <ScoreGauge score={nullFrac} warn={WARN_THRESHOLD} fail={FAIL_THRESHOLD} />
                <div className="flex justify-between mt-1">
                  <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>0%</span>
                  <span className="t-micro font-mono" style={{ color: "var(--warn)" }}>warn {WARN_THRESHOLD}%</span>
                  <span className="t-micro font-mono" style={{ color: "var(--fail)" }}>fail {FAIL_THRESHOLD}%</span>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="t-small" style={{ color: "var(--fg-1)" }}>Completeness</span>
                  <span className="t-small font-mono" style={{ color: "var(--pass)" }}>
                    {((1 - nullFrac) * 100).toFixed(2)}%
                  </span>
                </div>
                <div style={{ height: 6, background: "var(--bg-3)", width: "100%" }}>
                  <div style={{ height: "100%", width: `${(1 - nullFrac) * 100}%`, background: "var(--pass)", transition: "width 600ms ease" }} />
                </div>
              </div>
            </div>
          </div>

          {/* open incidents */}
          {columnIncidents.length > 0 && (
            <div className="border border-line" style={{ background: "var(--bg-1)" }}>
              <div className="px-4 py-3 border-b border-line flex items-center justify-between">
                <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Open incidents</span>
                <span className="t-micro px-1.5 py-0.5" style={{ background: "var(--fail-bg)", color: "var(--fail)", fontFamily: "var(--font-jetbrains-mono)" }}>
                  {columnIncidents.length}
                </span>
              </div>
              <div className="divide-y divide-line">
                {columnIncidents.map((inc) => (
                  <Link
                    key={inc.id}
                    href={`/incidents/${inc.id}` as never}
                    className="flex items-start gap-3 px-4 py-3 hover:bg-bg-2 transition-colors"
                    style={{ color: "inherit" }}
                  >
                    <span className="t-micro px-1.5 py-0.5 mt-0.5" style={{
                      background: inc.severity === "fail" ? "var(--fail-bg)" : "rgba(217,181,102,0.12)",
                      color: inc.severity === "fail" ? "var(--fail)" : "var(--warn)",
                      fontFamily: "var(--font-jetbrains-mono)", flexShrink: 0,
                    }}>
                      {inc.severity}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="t-small" style={{ color: "var(--fg-0)" }}>{inc.message}</p>
                      <p className="t-micro mt-0.5" style={{ color: "var(--fg-3)" }}>{inc.opened_ago}</p>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* all checks */}
          {checks.length > 1 && (
            <div className="border border-line" style={{ background: "var(--bg-1)" }}>
              <div className="px-4 py-3 border-b border-line t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                All tests ({checks.length})
              </div>
              <table className="w-full" style={{ borderCollapse: "collapse" }}>
                <thead>
                  <tr className="border-b border-line">
                    {["Detector", "Score", "Verdict", "Checked"].map((h) => (
                      <th key={h} className="px-4 py-2 text-left t-micro" style={{ color: "var(--fg-2)", fontWeight: 400, letterSpacing: "0.08em", textTransform: "uppercase" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {checks.map((c) => (
                    <tr key={c.id} className="border-b border-line last:border-0">
                      <td className="px-4 py-2.5 t-small font-mono" style={{ color: "var(--fg-0)" }}>{c.detector}</td>
                      <td className="px-4 py-2.5 t-small font-mono" style={{ color: "var(--fg-1)" }}>
                        {c.score !== null ? (c.score * 100).toFixed(3) + "%" : "--"}
                      </td>
                      <td className="px-4 py-2.5"><VerdictBadge verdict={c.verdict ?? "unknown"} /></td>
                      <td className="px-4 py-2.5 t-small" style={{ color: "var(--fg-3)" }}>{c.ran_at_ago}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* AI check suggestions */}
          <div className="border border-line" style={{ background: "var(--bg-1)" }}>
            <div
              className="px-4 py-3 border-b border-line t-micro"
              style={{
                color: "var(--fg-3)",
                letterSpacing: "0.08em",
                textTransform: "uppercase",
              }}
            >
              AI check suggestions
            </div>
            <SuggestPanel datasetId={id} column={column} />
          </div>
        </div>

        {/* right rail */}
        <div style={{ width: 360, flexShrink: 0 }} className="space-y-4">
          <div className="border border-line" style={{ background: "var(--bg-1)" }}>
            <div className="px-4 py-3 border-b border-line t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
              Test definition
            </div>
            <pre className="p-4 t-micro overflow-x-auto" style={{ color: "var(--fg-1)", fontFamily: "var(--font-jetbrains-mono)", lineHeight: 1.7, background: "var(--bg-2)", margin: 0 }}>
              {yamlDef}
            </pre>
          </div>

          <div className="border border-line" style={{ background: "var(--bg-1)" }}>
            <div className="px-4 py-3 border-b border-line t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
              Dataset context
            </div>
            <div className="divide-y divide-line">
              {[
                ["Dataset", id],
                ["Source", dataset.source],
                ["Schema", dataset.schema],
                ["Total rows", dataset.row_count?.toLocaleString() ?? "--"],
                ["Total columns", String(dataset.column_count ?? "--")],
                ["Dataset status", dataset.status],
                ["Last run", dataset.last_run],
              ].map(([label, value]) => (
                <div key={label} className="flex items-start justify-between gap-3 px-4 py-2.5">
                  <span className="t-micro" style={{ color: "var(--fg-3)", flexShrink: 0 }}>{label}</span>
                  <span className="t-small font-mono text-right" style={{ color: "var(--fg-1)" }}>{value}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="border border-line" style={{ background: "var(--bg-1)" }}>
            <div className="px-4 py-3 border-b border-line t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
              Activity
            </div>
            <div className="p-4 space-y-3">
              <div className="flex items-start gap-3">
                <span style={{ display: "inline-block", width: 6, height: 6, background: verdict === "fail" ? "var(--fail)" : verdict === "warn" ? "var(--warn)" : "var(--pass)", marginTop: 4, flexShrink: 0 }} />
                <div>
                  <p className="t-small" style={{ color: "var(--fg-1)" }}>Test ran — {verdict}</p>
                  <p className="t-micro mt-0.5" style={{ color: "var(--fg-3)" }}>{check.ran_at_ago}</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span style={{ display: "inline-block", width: 6, height: 6, background: "var(--fg-3)", marginTop: 4, flexShrink: 0 }} />
                <div>
                  <p className="t-small" style={{ color: "var(--fg-1)" }}>Null fraction computed</p>
                  <p className="t-micro mt-0.5" style={{ color: "var(--fg-3)" }}>
                    {nullCount.toLocaleString()} / {totalCount.toLocaleString()} rows scanned
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
