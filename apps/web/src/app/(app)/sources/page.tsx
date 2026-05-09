import Link from "next/link";
import { RefreshCw, Plus } from "lucide-react";

const MOCK_SOURCES = [
  {
    id: "analytics-prod", alias: "c_pg_prod",
    engine: "PostgreSQL", endpoint: "db.prod.internal:5432/analytics",
    tables: 184, lastSync: "2m ago", status: "pass",
  },
  {
    id: "acme-prod-1", alias: "c_bq_main",
    engine: "BigQuery", endpoint: "us · acme-prod-1.analytics",
    tables: 421, lastSync: "14m ago", status: "pass",
  },
  {
    id: "events-cluster", alias: "c_ch_events",
    engine: "ClickHouse", endpoint: "tenant.clickhouse.cloud:9440/events",
    tables: 38, lastSync: "1h ago", status: "warn",
  },
  {
    id: "legacy-orders", alias: "c_my_legacy",
    engine: "MySQL", endpoint: "mysql.prod.internal:3306/orders",
    tables: 64, lastSync: "3h ago", status: "warn",
  },
  {
    id: "staging", alias: "c_pg_stage",
    engine: "PostgreSQL", endpoint: "db.staging.internal:5432/analytics",
    tables: 173, lastSync: "failed", status: "fail",
  },
];

const ENGINE_CARDS = [
  {
    id: "postgres", name: "PostgreSQL",
    scheme: "postgresql://",
    desc: "Operational + analytical Postgres clusters. Read-replica recommended.",
    color: "#336791",
  },
  {
    id: "mysql", name: "MySQL",
    scheme: "mysql://",
    desc: "MySQL 5.7+ / 8.x. dqt issues read-only queries against a dedicated user.",
    color: "#E48E00",
  },
  {
    id: "bigquery", name: "BigQuery",
    scheme: "bigquery://",
    desc: "Google Cloud BigQuery. Authenticate with a service-account JSON key.",
    color: "#4285F4",
  },
  {
    id: "clickhouse", name: "ClickHouse",
    scheme: "clickhouse://",
    desc: "ClickHouse Cloud or self-hosted. Native protocol preferred for sample-heavy checks.",
    color: "#FBBC05",
  },
  {
    id: "snowflake", name: "Snowflake",
    scheme: "snowflake://",
    desc: "Snowflake account with a dedicated dqt warehouse + read-only role.",
    color: "#29B5E8",
  },
];

function StatusDot({ status }: { status: string }) {
  const color =
    status === "pass" ? "var(--pass)" :
    status === "warn" ? "var(--warn)" :
    "var(--fail)";
  return (
    <span
      style={{
        display: "inline-block",
        width: 7,
        height: 7,
        background: color,
        boxShadow: `0 0 0 2px ${color}28`,
        flexShrink: 0,
      }}
    />
  );
}

export default function SourcesPage() {
  return (
    <div className="p-6 max-w-5xl space-y-8">
      {/* header */}
      <div>
        <p className="t-micro mb-1" style={{ color: "var(--fg-3)", letterSpacing: "0.12em", textTransform: "uppercase" }}>
          Connections · 5 active · 2 with warnings
        </p>
        <div className="flex items-end justify-between">
          <div>
            <h1 className="t-display" style={{ color: "var(--fg-0)", fontWeight: 200 }}>Sources</h1>
            <p className="t-small mt-1" style={{ color: "var(--fg-2)", maxWidth: 560, lineHeight: 1.6 }}>
              Warehouses dqt watches. Tables here become <strong style={{ color: "var(--fg-1)", fontWeight: 500 }}>datasets</strong> in the semantic layer; metrics defined on top of them are what dqt baselines and explains.
            </p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              className="flex items-center gap-1.5 px-3 py-1.5 t-small border border-line transition-colors hover:bg-bg-2"
              style={{ color: "var(--fg-1)" }}
            >
              <RefreshCw size={11} strokeWidth={1.6} />
              Sync all
            </button>
            <Link
              href="/sources/new/postgres"
              className="flex items-center gap-1.5 px-3 py-1.5 t-small border transition-colors hover:opacity-80"
              style={{ background: "var(--bg-2)", color: "var(--fg-0)", borderColor: "var(--line-3)" }}
            >
              <Plus size={11} strokeWidth={1.6} />
              Add connection
            </Link>
          </div>
        </div>
      </div>

      {/* connections table */}
      <div className="border border-line" style={{ background: "var(--bg-1)" }}>
        <table className="w-full" style={{ borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "var(--bg-2)" }}>
              <th className="px-4 py-2 text-left t-micro" style={{ color: "var(--fg-3)", fontWeight: 400, letterSpacing: "0.1em", textTransform: "uppercase", width: 32 }} />
              <th className="px-4 py-2 text-left t-micro" style={{ color: "var(--fg-3)", fontWeight: 400, letterSpacing: "0.1em", textTransform: "uppercase" }}>Name</th>
              <th className="px-4 py-2 text-left t-micro" style={{ color: "var(--fg-3)", fontWeight: 400, letterSpacing: "0.1em", textTransform: "uppercase" }}>Engine</th>
              <th className="px-4 py-2 text-left t-micro" style={{ color: "var(--fg-3)", fontWeight: 400, letterSpacing: "0.1em", textTransform: "uppercase" }}>Endpoint</th>
              <th className="px-4 py-2 text-right t-micro" style={{ color: "var(--fg-3)", fontWeight: 400, letterSpacing: "0.1em", textTransform: "uppercase" }}>Tables</th>
              <th className="px-4 py-2 text-right t-micro" style={{ color: "var(--fg-3)", fontWeight: 400, letterSpacing: "0.1em", textTransform: "uppercase" }}>Last sync</th>
              <th className="px-4 py-2" style={{ width: 32 }} />
            </tr>
          </thead>
          <tbody>
            {MOCK_SOURCES.map((s) => (
              <tr key={s.id} className="border-t border-line hover:bg-bg-2 transition-colors cursor-pointer">
                <td className="px-4 py-3 text-center">
                  <StatusDot status={s.status} />
                </td>
                <td className="px-4 py-3">
                  <p className="t-small font-medium" style={{ color: "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)", fontWeight: 400 }}>{s.id}</p>
                  <p className="t-micro mt-0.5" style={{ color: "var(--fg-3)", fontFamily: "var(--font-jetbrains-mono)" }}>{s.alias}</p>
                </td>
                <td className="px-4 py-3 t-small" style={{ color: "var(--fg-1)" }}>{s.engine}</td>
                <td className="px-4 py-3 t-small font-mono" style={{ color: "var(--fg-1)" }}>{s.endpoint}</td>
                <td className="px-4 py-3 t-small text-right font-mono" style={{ color: "var(--fg-1)" }}>{s.tables}</td>
                <td
                  className="px-4 py-3 t-small text-right font-mono"
                  style={{ color: s.status === "fail" ? "var(--fail)" : s.status === "warn" ? "var(--warn)" : "var(--fg-2)" }}
                >
                  {s.lastSync}
                </td>
                <td className="px-4 py-3 t-small text-right" style={{ color: "var(--fg-3)" }}>›</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* add a source */}
      <div>
        <p className="t-micro mb-3" style={{ color: "var(--fg-3)", letterSpacing: "0.12em", textTransform: "uppercase" }}>
          Add a Source
        </p>
        <p className="t-small mb-4" style={{ color: "var(--fg-2)" }}>
          dqt only needs read access. We&apos;ll create a least-privilege user and verify before saving.
        </p>
        <div className="grid gap-3" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))" }}>
          {ENGINE_CARDS.map((e) => (
            <Link
              key={e.id}
              href={`/sources/new/${e.id}` as never}
              className="p-4 border border-line transition-colors hover:bg-bg-2 hover:border-line-3 block"
              style={{ background: "var(--bg-1)" }}
            >
              <div className="flex items-center gap-2 mb-2">
                <span
                  className="flex items-center justify-center w-6 h-6 t-micro font-medium"
                  style={{ background: e.color + "18", color: e.color, fontFamily: "var(--font-jetbrains-mono)" }}
                >
                  {e.name.slice(0, 2).toUpperCase()}
                </span>
                <span className="t-small font-medium" style={{ color: "var(--fg-0)" }}>{e.name}</span>
              </div>
              <p className="t-micro mb-1" style={{ color: "var(--fg-3)", fontFamily: "var(--font-jetbrains-mono)" }}>{e.scheme}</p>
              <p className="t-micro" style={{ color: "var(--fg-2)", lineHeight: 1.5 }}>{e.desc}</p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
