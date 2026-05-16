import Link from "next/link";

const FLEET_KPIS = [
  { label: "Open Incidents", value: "3", trend: "fail" },
  { label: "Datasets Watched", value: "6", trend: null },
  { label: "Tests Running", value: "46", trend: null },
  { label: "Auto-explained", value: "2", trend: "pass" },
] as const;

const ACTIVITY = [
  { time: "2 min ago", text: "gigler_transactions.platform_fee_usd failed null_fraction", kind: "fail" },
  { time: "5 min ago", text: "gig_vendor_stats baseline re-fit completed", kind: "pass" },
  { time: "12 min ago", text: "fct_orders freshness test passed", kind: "pass" },
  { time: "1h ago", text: "gig_prices ks2sample warned — distribution shift detected", kind: "warn" },
  { time: "2h ago", text: "AI agent explained incident #41 — conversion drop traced to fee changes", kind: "info" },
] as const;

type Trend = "pass" | "warn" | "fail" | null;

function TrendDot({ trend }: { trend: Trend }) {
  if (!trend) return null;
  const color = trend === "pass" ? "var(--pass)" : trend === "warn" ? "var(--warn)" : "var(--fail)";
  return (
    <span
      style={{
        display: "inline-block",
        width: 7,
        height: 7,
        background: color,
        boxShadow: `0 0 0 2px ${color}28`,
        marginLeft: 6,
        verticalAlign: "middle",
      }}
    />
  );
}

export default function OverviewPage() {
  return (
    <div className="p-6 w-full">
      <h1 className="t-h1 mb-6" style={{ color: "var(--fg-0)" }}>Overview</h1>

      {/* KPI band */}
      <div className="grid grid-cols-4 gap-px border border-line mb-8" style={{ background: "var(--line)" }}>
        {FLEET_KPIS.map((k) => (
          <div
            key={k.label}
            className="px-5 py-4"
            style={{ background: "var(--bg-1)" }}
          >
            <p className="kpi-label mb-2" style={{ color: "var(--fg-2)" }}>{k.label}</p>
            <p className="kpi-value">
              {k.value}
              <TrendDot trend={k.trend as Trend} />
            </p>
          </div>
        ))}
      </div>

      {/* datasets + activity */}
      <div className="grid grid-cols-2 gap-6">
        {/* datasets shortcut */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="t-h3" style={{ color: "var(--fg-0)" }}>Datasets</h2>
            <Link href="/datasets" className="t-small" style={{ color: "var(--accent)" }}>
              View all →
            </Link>
          </div>
          <div className="border border-line" style={{ background: "var(--bg-1)" }}>
            {[
              { id: "gigler_transactions", status: "fail" },
              { id: "gig_prices", status: "warn" },
              { id: "fct_sessions", status: "warn" },
              { id: "marketing_campaigns", status: "pass" },
              { id: "fct_orders", status: "pass" },
              { id: "gig_vendor_stats", status: "pass" },
            ].map((ds, i) => {
              const color = ds.status === "pass" ? "var(--pass)" : ds.status === "warn" ? "var(--warn)" : "var(--fail)";
              return (
                <Link
                  key={ds.id}
                  href={`/datasets/${ds.id}`}
                  className="flex items-center justify-between px-3 py-2 border-b border-line last:border-0 transition-colors hover:bg-bg-2"
                  style={{ color: "var(--fg-0)" }}
                >
                  <span className="t-small font-mono">{ds.id}</span>
                  <span style={{ display: "inline-block", width: 7, height: 7, background: color, boxShadow: `0 0 0 2px ${color}28` }} />
                </Link>
              );
            })}
          </div>
        </div>

        {/* activity feed */}
        <div>
          <h2 className="t-h3 mb-3" style={{ color: "var(--fg-0)" }}>Activity</h2>
          <div className="space-y-0 border border-line" style={{ background: "var(--bg-1)" }}>
            {ACTIVITY.map((a, i) => {
              const color =
                a.kind === "pass"
                  ? "var(--pass)"
                  : a.kind === "warn"
                  ? "var(--warn)"
                  : a.kind === "fail"
                  ? "var(--fail)"
                  : "var(--fg-2)";
              return (
                <div
                  key={i}
                  className="flex items-start gap-3 px-3 py-2 border-b border-line last:border-0"
                >
                  <span
                    style={{
                      display: "inline-block",
                      width: 6,
                      height: 6,
                      background: color,
                      marginTop: 4,
                      flexShrink: 0,
                    }}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="t-small" style={{ color: "var(--fg-1)", lineHeight: 1.5 }}>
                      {a.text}
                    </p>
                    <p className="t-micro mt-0.5" style={{ color: "var(--fg-3)" }}>{a.time}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
