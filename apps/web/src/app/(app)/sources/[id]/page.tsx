import Link from "next/link";
import { notFound } from "next/navigation";
import { serverFetch } from "@/lib/server-api";
import { SourceEditForm } from "./source-edit-form";

interface SourceDetail {
  id: string;
  name: string;
  engine: string;
  endpoint: string;
  host: string;
  port: number;
  tables: number;
  status: string;
  last_sync: string;
}

function StatusDot({ status }: { status: string }) {
  const color =
    status === "pass" ? "var(--pass)" :
    status === "warn" ? "var(--warn)" :
    status === "fail" ? "var(--fail)" : "var(--fg-3)";
  return (
    <span
      style={{ display: "inline-block", width: 7, height: 7, background: color, boxShadow: `0 0 0 2px ${color}28`, flexShrink: 0 }}
    />
  );
}

export default async function SourceDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const source = await serverFetch<SourceDetail>(`/sources/${encodeURIComponent(id)}`, 30);

  if (!source) notFound();

  const engineId = source.engine.toLowerCase().replace(/sql$/, "").replace("postgresql", "postgres");

  return (
    <div className="p-6 max-w-2xl fade-in">
      {/* breadcrumb */}
      <div className="flex items-center gap-2 mb-6">
        <Link href="/sources" className="flex items-center gap-1.5 t-small transition-colors hover:opacity-80" style={{ color: "var(--accent)", fontFamily: "var(--font-jetbrains-mono)" }}>
          <span style={{ fontSize: 14, lineHeight: 1 }}>←</span>
          <span>Sources</span>
        </Link>
        <span style={{ color: "var(--fg-3)", fontSize: 12 }}>/</span>
        <span className="t-small font-mono" style={{ color: "var(--fg-2)" }}>{source.name}</span>
      </div>

      {/* header */}
      <div className="flex items-center gap-3 mb-8">
        <StatusDot status={source.status} />
        <h1 className="t-h1 font-mono" style={{ color: "var(--fg-0)" }}>{source.name}</h1>
        <span className="t-small" style={{ color: "var(--fg-3)" }}>{source.engine}</span>
      </div>

      {/* KPI band */}
      <div className="grid grid-cols-3 gap-px border border-line mb-8" style={{ background: "var(--line)" }}>
        {[
          { label: "Status", value: source.status },
          { label: "Tables", value: String(source.tables) },
          { label: "Last sync", value: source.last_sync },
        ].map((k) => (
          <div key={k.label} className="px-5 py-4" style={{ background: "var(--bg-1)" }}>
            <p className="kpi-label mb-1" style={{ color: "var(--fg-2)" }}>{k.label}</p>
            <p className="t-small font-mono" style={{ color: "var(--fg-0)" }}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* connection edit form */}
      <div className="border border-line mb-6" style={{ background: "var(--bg-1)" }}>
        <div className="px-4 py-3 border-b border-line">
          <p className="t-small font-medium" style={{ color: "var(--fg-0)" }}>Connection settings</p>
        </div>
        <div className="px-4 py-5">
          <SourceEditForm
            engine={engineId}
            sourceId={source.id}
            initialValues={{
              host: source.host,
              port: String(source.port),
            }}
          />
        </div>
      </div>
    </div>
  );
}
