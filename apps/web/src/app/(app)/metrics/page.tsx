import Link from "next/link";
import { serverFetch } from "@/lib/server-api";

interface MetricSummary {
  fqn: string;
  display_name: string;
  kind: string;
  dataset: string;
  owners: string[];
  tags: string[];
  current_verdict: string | null;
  last_run: string | null;
  pinned: boolean;
}

function VerdictDot({ verdict }: { verdict: string | null }) {
  const color =
    verdict === "pass" ? "var(--pass)" :
    verdict === "fail" ? "var(--fail)" :
    verdict === "warn" ? "var(--warn)" : "var(--fg-3)";
  return (
    <span style={{
      display: "inline-block", width: 8, height: 8,
      background: color, boxShadow: `0 0 0 2px ${color}28`, flexShrink: 0,
    }} />
  );
}

export default async function MetricsPage() {
  const metrics = await serverFetch<MetricSummary[]>("/metrics", 30) ?? [];

  return (
    <div className="p-6">
      <div className="flex items-baseline justify-between mb-6">
        <h1 className="t-h1" style={{ color: "var(--fg-0)" }}>Metrics</h1>
        <span className="t-small" style={{ color: "var(--fg-3)" }}>{metrics.length} tracked</span>
      </div>
      <div className="border border-line" style={{ background: "var(--bg-1)" }}>
        <table className="w-full" style={{ borderCollapse: "collapse" }}>
          <thead>
            <tr className="border-b border-line">
              {["", "Metric", "Dataset", "Kind", "Owners", "Last run"].map((h, i) => (
                <th key={i} className="px-3 py-2 text-left t-micro"
                    style={{ color: "var(--fg-2)", fontWeight: 400, letterSpacing: "0.08em", textTransform: "uppercase" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {metrics.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center t-small" style={{ color: "var(--fg-3)" }}>
                  No metrics tracked yet. Connect a source and run checks to generate metrics.
                </td>
              </tr>
            ) : metrics.map((m) => (
              <tr key={m.fqn} className="border-b border-line last:border-0 hover:bg-bg-2 transition-colors">
                <td className="px-3 py-2" style={{ width: 32 }}>
                  <VerdictDot verdict={m.current_verdict} />
                </td>
                <td className="px-3 py-2">
                  <Link href={`/metrics/${encodeURIComponent(m.fqn)}`}
                        className="t-small font-mono hover:underline"
                        style={{ color: "var(--accent)" }}>
                    {m.display_name}
                  </Link>
                  <p className="t-micro mt-0.5 font-mono" style={{ color: "var(--fg-3)" }}>{m.fqn}</p>
                </td>
                <td className="px-3 py-2 t-small" style={{ color: "var(--fg-1)" }}>{m.dataset}</td>
                <td className="px-3 py-2 t-small font-mono" style={{ color: "var(--fg-2)" }}>{m.kind}</td>
                <td className="px-3 py-2 t-small" style={{ color: "var(--fg-2)" }}>{m.owners.join(", ")}</td>
                <td className="px-3 py-2 t-small" style={{ color: "var(--fg-3)" }}>{m.last_run ?? "--"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
