import Link from "next/link";

type Engine = {
  id: string;
  name: string;
  initial: string;
  color: string;
};

export function EngineCard({ engine }: { engine: Engine }) {
  return (
    <Link
      href={`/sources/new/${engine.id}`}
      className="flex flex-col items-center gap-2 p-4 border border-line transition-colors hover:bg-bg-2"
      style={{ background: "var(--bg-1)", minWidth: 100 }}
    >
      {/* placeholder glyph */}
      <div
        className="w-10 h-10 flex items-center justify-center t-h3 font-mono"
        style={{
          background: engine.color + "18",
          color: engine.color,
          border: `1px solid ${engine.color}40`,
        }}
      >
        {engine.initial}
      </div>
      <span className="t-small" style={{ color: "var(--fg-1)" }}>
        {engine.name}
      </span>
    </Link>
  );
}

export const ENGINES: Engine[] = [
  { id: "bigquery", name: "BigQuery", initial: "BQ", color: "#4285F4" },
  { id: "postgres", name: "PostgreSQL", initial: "PG", color: "#336791" },
  { id: "mysql", name: "MySQL", initial: "MY", color: "#00758F" },
  { id: "snowflake", name: "Snowflake", initial: "SF", color: "#29B5E8" },
];
