import Link from "next/link";

const ENGINES = [
  {
    id: "postgres",
    name: "PostgreSQL",
    scheme: "postgresql://",
    desc: "Operational + analytical Postgres clusters.",
    color: "#336791",
  },
  {
    id: "mysql",
    name: "MySQL",
    scheme: "mysql://",
    desc: "MySQL 5.7+ / 8.x.",
    color: "#E48E00",
  },
  {
    id: "clickhouse",
    name: "ClickHouse",
    scheme: "clickhouse://",
    desc: "ClickHouse Cloud or self-hosted.",
    color: "#FBBC05",
  },
  {
    id: "bigquery",
    name: "BigQuery",
    scheme: "bigquery://",
    desc: "Google Cloud BigQuery with service-account JSON.",
    color: "#4285F4",
  },
  {
    id: "snowflake",
    name: "Snowflake",
    scheme: "snowflake://",
    desc: "Snowflake with a dedicated read-only role.",
    color: "#29B5E8",
  },
] as const;

export default function NewSourcePickerPage() {
  return (
    <div className="p-6 max-w-2xl">
      <div className="flex items-center gap-2 mb-6">
        <Link href="/sources" className="flex items-center gap-1.5 t-small transition-colors hover:opacity-80" style={{ color: "var(--accent)", fontFamily: "var(--font-jetbrains-mono)" }}>
          <span style={{ fontSize: 14, lineHeight: 1 }}>←</span>
          <span>Sources</span>
        </Link>
        <span style={{ color: "var(--fg-3)", fontSize: 12 }}>/</span>
        <span className="t-small font-mono" style={{ color: "var(--fg-2)" }}>new</span>
      </div>
      <h1 className="t-h1 mb-2" style={{ color: "var(--fg-0)" }}>Add connection</h1>
      <p className="t-small mb-8" style={{ color: "var(--fg-2)" }}>
        dqt only needs read access. Choose your warehouse engine to continue.
      </p>

      <div className="grid gap-3" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))" }}>
        {ENGINES.map((e) => (
          <Link
            key={e.id}
            href={`/sources/new/${e.id}`}
            className="p-4 border border-line transition-colors hover:bg-bg-2 hover:border-line-3 block"
            style={{ background: "var(--bg-1)" }}
          >
            <div className="flex items-center gap-2 mb-2">
              <span
                className="flex items-center justify-center w-6 h-6 t-micro font-medium"
                style={{
                  background: e.color + "18",
                  color: e.color,
                  fontFamily: "var(--font-jetbrains-mono)",
                }}
              >
                {e.name.slice(0, 2).toUpperCase()}
              </span>
              <span className="t-small font-medium" style={{ color: "var(--fg-0)" }}>
                {e.name}
              </span>
            </div>
            <p className="t-micro mb-1" style={{ color: "var(--fg-3)", fontFamily: "var(--font-jetbrains-mono)" }}>
              {e.scheme}
            </p>
            <p className="t-micro" style={{ color: "var(--fg-2)", lineHeight: 1.5 }}>
              {e.desc}
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}
