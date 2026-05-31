"use client";

interface ColumnStats {
  total_count: number | null;
  null_count: number | null;
  zero_count: number | null;
  empty_count: number | null;
  distinct_count: number | null;
  kind: string;
}

interface RunPoint {
  id: number;
  detector: string;
  score: number | null;
  verdict: string | null;
  ran_at: string;
}

function fmtNum(v: number | null): string {
  if (v === null) return "--";
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return v.toLocaleString();
}

function fmtPct(v: number | null, d = 1): string {
  if (v === null) return "--";
  return `${(v * 100).toFixed(d)}%`;
}

function NullBar({ pct }: { pct: number }) {
  const filled = Math.max(0, Math.min(1, pct));
  const W = 600, H = 20;
  const filledW = filled * W;

  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.06em", textTransform: "uppercase" }}>
          Null rate
        </span>
        <span className="t-small font-mono" style={{
          color: pct > 0.1 ? "var(--fail)" : pct > 0.01 ? "var(--warn)" : "var(--pass)",
          fontFamily: "var(--font-jetbrains-mono)",
        }}>
          {fmtPct(pct)}
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: 10, display: "block" }}>
        <rect x={0} y={0} width={W} height={H} fill="var(--bg-2)" />
        {filledW > 0 && (
          <rect x={0} y={0} width={filledW} height={H}
            fill={pct > 0.1 ? "var(--fail)" : pct > 0.01 ? "var(--warn)" : "var(--pass)"}
            opacity={0.8}
          />
        )}
      </svg>
    </div>
  );
}

function MetricCell({ label, value, sub, color }: {
  label: string;
  value: string;
  sub?: string;
  color?: string;
}) {
  return (
    <div className="px-4 py-3 border border-line" style={{ background: "var(--bg-0)" }}>
      <p className="t-micro mb-1" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
        {label}
      </p>
      <p className="font-mono" style={{
        fontSize: 20, fontWeight: 300, color: color ?? "var(--fg-0)",
        fontFamily: "var(--font-jetbrains-mono)", lineHeight: 1.2,
      }}>
        {value}
      </p>
      {sub && <p className="t-micro mt-0.5" style={{ color: "var(--fg-3)" }}>{sub}</p>}
    </div>
  );
}

export function CompletenessPanel({
  stats,
  history,
}: {
  stats: ColumnStats | null;
  history: RunPoint[];
}) {
  if (!stats || stats.total_count === null) {
    return (
      <div className="border border-line" style={{ background: "var(--bg-1)" }}>
        <div className="px-4 py-2.5 border-b border-line">
          <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Completeness</span>
        </div>
        <div className="px-4 py-8 t-small flex items-center justify-center" style={{ color: "var(--fg-3)" }}>
          No profile data
        </div>
      </div>
    );
  }

  const total = stats.total_count;
  const nullCount = stats.null_count ?? 0;
  const zeroCount = stats.zero_count ?? 0;
  const emptyCount = stats.empty_count ?? 0;
  const distinctCount = stats.distinct_count ?? 0;

  const nullPct = total > 0 ? nullCount / total : 0;
  const zeroPct = total > 0 ? zeroCount / total : null;
  const emptyPct = total > 0 ? emptyCount / total : null;
  const distinctPct = total > 0 ? distinctCount / total : null;

  // Latest null_fraction check result from history
  const latestNullCheck = [...history]
    .filter(r => r.detector === "null_fraction" && r.score !== null)
    .sort((a, b) => new Date(b.ran_at).getTime() - new Date(a.ran_at).getTime())[0];

  return (
    <div className="border border-line" style={{ background: "var(--bg-1)" }}>
      <div className="px-4 py-2.5 border-b border-line flex items-center justify-between">
        <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Completeness</span>
        {latestNullCheck && (
          <span className="t-micro font-mono" style={{
            color: (latestNullCheck.verdict === "fail" ? "var(--fail)" : latestNullCheck.verdict === "warn" ? "var(--warn)" : "var(--pass)"),
            fontFamily: "var(--font-jetbrains-mono)",
          }}>
            {latestNullCheck.verdict?.toUpperCase()}
          </span>
        )}
      </div>
      <div className="px-4 py-4">
        {/* Null bar */}
        <NullBar pct={nullPct} />

        {/* 6-cell stats grid */}
        <div className="mt-4" style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 6 }}>
          <MetricCell
            label="Total rows"
            value={fmtNum(total)}
          />
          <MetricCell
            label="Non-null"
            value={fmtNum(total - nullCount)}
            sub={fmtPct(total > 0 ? (total - nullCount) / total : null)}
            color="var(--pass)"
          />
          <MetricCell
            label="Null"
            value={fmtNum(nullCount)}
            sub={fmtPct(nullPct)}
            color={nullPct > 0.1 ? "var(--fail)" : nullPct > 0.01 ? "var(--warn)" : "var(--fg-0)"}
          />
          <MetricCell
            label="Distinct"
            value={fmtNum(distinctCount)}
            sub={fmtPct(distinctPct)}
          />
          {stats.kind === "numeric" ? (
            <MetricCell
              label="Zero"
              value={fmtNum(zeroCount)}
              sub={fmtPct(zeroPct)}
              color={zeroPct !== null && zeroPct > 0.05 ? "var(--warn)" : undefined}
            />
          ) : (
            <MetricCell
              label="Empty"
              value={fmtNum(emptyCount)}
              sub={fmtPct(emptyPct)}
              color={emptyPct !== null && emptyPct > 0.05 ? "var(--warn)" : undefined}
            />
          )}
          <MetricCell
            label="Unique %"
            value={fmtPct(distinctPct)}
          />
        </div>
      </div>
    </div>
  );
}
