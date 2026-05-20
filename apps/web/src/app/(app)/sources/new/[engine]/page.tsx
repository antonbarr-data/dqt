import Link from "next/link";
import { Wizard } from "@/components/connections/wizard";

const ENGINE_META: Record<string, { name: string; abbr: string; color: string; desc: string }> = {
  postgres:   { name: "PostgreSQL",  abbr: "PG", color: "#336791", desc: "Operational + analytical Postgres clusters" },
  mysql:      { name: "MySQL",       abbr: "MY", color: "#E48E00", desc: "MySQL 5.7+ / 8.x" },
  clickhouse: { name: "ClickHouse",  abbr: "CH", color: "#FBBC05", desc: "ClickHouse Cloud or self-hosted" },
  bigquery:   { name: "BigQuery",    abbr: "BQ", color: "#4285F4", desc: "Google Cloud BigQuery" },
  snowflake:  { name: "Snowflake",   abbr: "SF", color: "#29B5E8", desc: "Snowflake with a dedicated read-only role" },
};

interface Props {
  params: { engine: string };
}

export default function NewSourcePage({ params }: Props) {
  const meta = ENGINE_META[params.engine] ?? {
    name: params.engine,
    abbr: params.engine.slice(0, 2).toUpperCase(),
    color: "var(--accent)",
    desc: "",
  };

  return (
    <div className="min-h-full" style={{ background: "var(--bg-0)" }}>
      <div className="max-w-4xl mx-auto px-8 py-8">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 mb-8">
          <Link
            href="/sources"
            className="t-small transition-colors hover:opacity-80"
            style={{ color: "var(--fg-2)", fontFamily: "var(--font-jetbrains-mono)" }}
          >
            Sources
          </Link>
          <span style={{ color: "var(--fg-3)", fontSize: 12 }}>/</span>
          <span className="t-small font-mono" style={{ color: "var(--fg-0)" }}>New {meta.name} Connection</span>
        </div>

        {/* Header */}
        <div className="flex items-center gap-4 mb-10">
          <div
            className="flex items-center justify-center flex-shrink-0"
            style={{
              width: 44,
              height: 44,
              background: meta.color,
              color: "#fff",
              fontSize: 13,
              fontWeight: 600,
              fontFamily: "var(--font-jetbrains-mono)",
              letterSpacing: "0.03em",
            }}
          >
            {meta.abbr}
          </div>
          <div>
            <p
              className="t-micro font-medium uppercase"
              style={{ color: "var(--fg-3)", letterSpacing: "0.1em", marginBottom: 3 }}
            >
              new connection
            </p>
            <h1 className="t-h1 leading-none" style={{ color: "var(--fg-0)" }}>{meta.name}</h1>
            {meta.desc && (
              <p className="t-small mt-1" style={{ color: "var(--fg-2)" }}>{meta.desc}</p>
            )}
          </div>
        </div>

        <Wizard engine={params.engine} />
      </div>
    </div>
  );
}
