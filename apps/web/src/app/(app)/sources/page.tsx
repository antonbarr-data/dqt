import Link from "next/link";
import { EngineCard, ENGINES } from "@/components/connections/engine-card";
import { Plus } from "lucide-react";

const MOCK_SOURCES = [
  { id: "gigler_warehouse", engine: "bigquery", detail: "gigler-data-prod", status: "connected", datasets: 4, lastPing: "30s ago" },
  { id: "demo_warehouse", engine: "postgres", detail: "localhost:5434", status: "connected", datasets: 2, lastPing: "1 min ago" },
];

export default function SourcesPage() {
  return (
    <div className="p-6">
      {/* page header */}
      <div className="flex items-center justify-between mb-5">
        <h1 className="t-h1" style={{ color: "var(--fg-0)" }}>Sources</h1>
        <Link
          href="/sources/new/bigquery"
          className="flex items-center gap-1.5 px-3 py-1.5 t-small border border-line transition-colors hover:bg-bg-2"
          style={{ color: "var(--fg-1)" }}
        >
          <Plus size={13} strokeWidth={1.6} />
          Add Connection
        </Link>
      </div>

      {/* engine selection */}
      <div className="mb-6">
        <p className="t-small mb-3" style={{ color: "var(--fg-2)" }}>
          Connect a new data source
        </p>
        <div className="flex gap-2">
          {ENGINES.map((e) => (
            <EngineCard key={e.id} engine={e} />
          ))}
        </div>
      </div>

      {/* existing connections */}
      <div>
        <h2 className="t-h3 mb-3" style={{ color: "var(--fg-0)" }}>Connections</h2>
        <div className="border border-line" style={{ background: "var(--bg-1)" }}>
          <table className="w-full" style={{ borderCollapse: "collapse" }}>
            <thead>
              <tr className="border-b border-line">
                {["Name", "Engine", "Detail", "Status", "Datasets", "Last Ping"].map((h) => (
                  <th
                    key={h}
                    className="px-3 py-2 text-left t-micro"
                    style={{
                      color: "var(--fg-2)",
                      fontWeight: 400,
                      letterSpacing: "0.08em",
                      textTransform: "uppercase",
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {MOCK_SOURCES.map((s) => (
                <tr
                  key={s.id}
                  className="border-b border-line last:border-0 hover:bg-bg-2 transition-colors"
                >
                  <td className="px-3 py-2">
                    <span className="t-body font-mono" style={{ color: "var(--fg-0)" }}>
                      {s.id}
                    </span>
                  </td>
                  <td className="px-3 py-2 t-small" style={{ color: "var(--fg-1)" }}>
                    {s.engine}
                  </td>
                  <td className="px-3 py-2 t-small font-mono" style={{ color: "var(--fg-1)" }}>
                    {s.detail}
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className="t-small"
                      style={{
                        color: s.status === "connected" ? "var(--pass)" : "var(--fail)",
                      }}
                    >
                      <span
                        style={{
                          display: "inline-block",
                          width: 6,
                          height: 6,
                          background: s.status === "connected" ? "var(--pass)" : "var(--fail)",
                          marginRight: 5,
                          verticalAlign: "middle",
                        }}
                      />
                      {s.status}
                    </span>
                  </td>
                  <td className="px-3 py-2 t-small font-mono" style={{ color: "var(--fg-1)" }}>
                    {s.datasets}
                  </td>
                  <td className="px-3 py-2 t-small" style={{ color: "var(--fg-2)" }}>
                    {s.lastPing}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
