import Link from "next/link";
import { Wizard } from "@/components/connections/wizard";
import { EngineIcon } from "@/components/connections/engine-icon";

const ENGINE_META: Record<string, { name: string; desc: string }> = {
  postgres:   { name: "PostgreSQL",  desc: "Operational + analytical Postgres clusters" },
  mysql:      { name: "MySQL",       desc: "MySQL 5.7+ / 8.x" },
  clickhouse: { name: "ClickHouse",  desc: "ClickHouse Cloud or self-hosted" },
  bigquery:   { name: "BigQuery",    desc: "Google Cloud BigQuery" },
  snowflake:  { name: "Snowflake",   desc: "Snowflake with a dedicated read-only role" },
};

interface Props {
  params: { engine: string };
}

export default function NewSourcePage({ params }: Props) {
  const meta = ENGINE_META[params.engine] ?? { name: params.engine, desc: "" };

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
          <EngineIcon engine={params.engine} size={44} />
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
