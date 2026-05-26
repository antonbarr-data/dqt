import Link from "next/link";
import { EngineIcon } from "./engine-icon";

type Engine = {
  id: string;
  name: string;
  color: string;
};

export function EngineCard({ engine }: { engine: Engine }) {
  return (
    <Link
      href={`/sources/new/${engine.id}`}
      className="flex flex-col items-center gap-2 p-4 border border-line transition-colors hover:bg-bg-2"
      style={{ background: "var(--bg-1)", minWidth: 100 }}
    >
      <EngineIcon engine={engine.id} size={40} />
      <span className="t-small" style={{ color: "var(--fg-1)" }}>
        {engine.name}
      </span>
    </Link>
  );
}

export const ENGINES: Engine[] = [
  { id: "bigquery", name: "BigQuery", color: "#4285F4" },
  { id: "postgres", name: "PostgreSQL", color: "#336791" },
  { id: "mysql", name: "MySQL", color: "#00758F" },
  { id: "snowflake", name: "Snowflake", color: "#29B5E8" },
];
