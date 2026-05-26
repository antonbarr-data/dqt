"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Download, Trash2, Loader2 } from "lucide-react";
import { EngineIcon } from "@/components/connections/engine-icon";

interface Source {
  id: string;
  name: string;
  engine: string;
  endpoint: string;
  tables: number | string;
  status: string;
  last_sync: string;
}

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

// ---------------------------------------------------------------------------
// First-source blocking overlay
// ---------------------------------------------------------------------------

function ConnectWarehouseOverlay() {
  const router = useRouter();
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "var(--bg-0)",
        zIndex: 100,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "40px 24px",
      }}
    >
      <div style={{ maxWidth: 900, width: "100%" }}>
        <p
          className="t-micro mb-3"
          style={{ color: "var(--fg-3)", letterSpacing: "0.14em", textTransform: "uppercase" }}
        >
          Connect a Warehouse
        </p>
        <p className="t-small mb-8" style={{ color: "var(--fg-2)", maxWidth: 540, lineHeight: 1.6 }}>
          dqt only needs read access. We&apos;ll create a least-privilege user and verify the connection before saving.
        </p>
        <div className="grid gap-3" style={{ gridTemplateColumns: "repeat(5, 1fr)" }}>
          {ENGINE_CARDS.map((e) => (
            <button
              key={e.id}
              onClick={() => router.push(`/sources/new/${e.id}` as never)}
              className="p-4 border border-line text-left transition-colors hover:bg-bg-2 hover:border-line-3"
              style={{ background: "var(--bg-1)" }}
            >
              <div className="flex items-center gap-2 mb-2">
                <EngineIcon engine={e.id} size={24} />
                <span className="t-small font-medium" style={{ color: "var(--fg-0)" }}>{e.name}</span>
              </div>
              <p className="t-micro mb-1" style={{ color: "var(--fg-3)", fontFamily: "var(--font-jetbrains-mono)" }}>
                {e.scheme}
              </p>
              <p className="t-micro" style={{ color: "var(--fg-2)", lineHeight: 1.5 }}>{e.desc}</p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function SourcesPage() {
  const router = useRouter();
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const loadSources = useCallback(async () => {
    try {
      const res = await fetch("/api/v1/sources");
      if (res.ok) {
        setSources(await res.json());
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadSources(); }, [loadSources]);

  async function handleDelete(id: string) {
    setDeleting(true);
    try {
      await fetch(`/api/v1/sources/${encodeURIComponent(id)}`, { method: "DELETE" });
      setSources((prev) => prev.filter((s) => s.id !== id));
    } finally {
      setDeleting(false);
      setConfirmDeleteId(null);
    }
  }

  const activeCount = sources.filter((s) => s.status !== "fail").length;

  return (
    <>
      {/* Blocking overlay when no sources connected */}
      {!loading && sources.length === 0 && <ConnectWarehouseOverlay />}

      <div className="p-6 max-w-5xl space-y-8">
        {/* header */}
        <div>
          <p className="t-micro mb-1" style={{ color: "var(--fg-3)", letterSpacing: "0.12em", textTransform: "uppercase" }}>
            Connections · {loading ? "--" : `${activeCount} active`}
          </p>
          <div className="flex items-end justify-between">
            <div>
              <h1 className="t-display" style={{ color: "var(--fg-0)", fontWeight: 200 }}>Sources</h1>
              <p className="t-small mt-1" style={{ color: "var(--fg-2)", maxWidth: 560, lineHeight: 1.6 }}>
                Warehouses dqt watches. Tables here become <strong style={{ color: "var(--fg-1)", fontWeight: 500 }}>datasets</strong> in the semantic layer; metrics defined on top of them are what dqt baselines and explains.
              </p>
            </div>
          </div>
        </div>

        {/* connections table */}
        <div className="border border-line" style={{ background: "var(--bg-1)" }}>
          <table className="w-full" style={{ borderCollapse: "collapse" }}>
            <thead>
              <tr className="border-b border-line">
                {["", "Name", "Engine", "Endpoint", "Tables", "Last sync", "", "", ""].map((h, i) => (
                  <th
                    key={i}
                    className={`px-3 py-2 t-micro ${i === 4 || i === 5 ? "text-right" : "text-left"}`}
                    style={{ color: "var(--fg-2)", fontWeight: 400, letterSpacing: "0.08em", textTransform: "uppercase" }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={9} className="px-3 py-6 text-center t-small" style={{ color: "var(--fg-3)" }}>
                    Loading sources...
                  </td>
                </tr>
              ) : sources.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-3 py-6 text-center t-small" style={{ color: "var(--fg-3)" }}>
                    No sources connected yet.
                  </td>
                </tr>
              ) : sources.map((s) => (
                <tr
                  key={s.id}
                  className="border-b border-line last:border-0 hover:bg-bg-2 transition-colors cursor-pointer"
                  onClick={() => router.push(`/sources/${s.id}` as never)}
                >
                  <td className="px-3 py-2" style={{ width: 32 }}>
                    <StatusDot status={s.status} />
                  </td>
                  <td className="px-3 py-2">
                    <p className="t-small" style={{ color: "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)" }}>{s.name}</p>
                    <p className="t-micro mt-0.5" style={{ color: "var(--fg-3)", fontFamily: "var(--font-jetbrains-mono)" }}>{s.id}</p>
                  </td>
                  <td className="px-3 py-2 t-small" style={{ color: "var(--fg-1)" }}>{s.engine}</td>
                  <td className="px-3 py-2 t-small font-mono" style={{ color: "var(--fg-1)" }}>{s.endpoint}</td>
                  <td className="px-3 py-2 t-small text-right font-mono" style={{ color: "var(--fg-1)" }}>
                    {s.tables ?? "--"}
                  </td>
                  <td
                    className="px-3 py-2 t-small text-right font-mono"
                    style={{ color: s.status === "fail" ? "var(--fail)" : s.status === "warn" ? "var(--warn)" : "var(--fg-2)" }}
                  >
                    {s.last_sync ?? "--"}
                  </td>
                  <td className="px-3 py-2 t-small text-right" style={{ color: "var(--fg-3)" }}>
                    <a
                      href={`/api/v1/sources/${s.id}/export`}
                      download
                      onClick={e => e.stopPropagation()}
                      className="inline-flex items-center justify-center w-6 h-6 border border-transparent hover:border-line transition-colors"
                      style={{ color: "var(--fg-3)" }}
                      title="Download YAML bundle"
                    >
                      <Download size={11} strokeWidth={1.6} />
                    </a>
                  </td>
                  <td
                    className="px-3 py-2 text-right"
                    style={{ width: 120 }}
                    onClick={e => e.stopPropagation()}
                  >
                    {confirmDeleteId === s.id ? (
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleDelete(s.id)}
                          disabled={deleting}
                          className="flex items-center gap-1 px-2 py-0.5 t-micro border transition-colors"
                          style={{ borderColor: "var(--fail)", color: "var(--fail)", background: "rgba(224,123,110,0.08)" }}
                        >
                          {deleting
                            ? <Loader2 size={10} strokeWidth={2} className="animate-spin" />
                            : "delete"}
                        </button>
                        <button
                          onClick={() => setConfirmDeleteId(null)}
                          className="t-micro px-1 transition-colors hover:opacity-60"
                          style={{ color: "var(--fg-3)" }}
                        >
                          x
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setConfirmDeleteId(s.id)}
                        className="inline-flex items-center justify-center w-6 h-6 border border-transparent hover:border-line transition-colors ml-auto"
                        style={{ color: "var(--fg-3)" }}
                        title="Delete source"
                      >
                        <Trash2 size={11} strokeWidth={1.6} />
                      </button>
                    )}
                  </td>
                  <td className="px-3 py-2 t-small text-right" style={{ color: "var(--fg-3)" }}>›</td>
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
                  <EngineIcon engine={e.id} size={24} />
                  <span className="t-small font-medium" style={{ color: "var(--fg-0)" }}>{e.name}</span>
                </div>
                <p className="t-micro mb-1" style={{ color: "var(--fg-3)", fontFamily: "var(--font-jetbrains-mono)" }}>{e.scheme}</p>
                <p className="t-micro" style={{ color: "var(--fg-2)", lineHeight: 1.5 }}>{e.desc}</p>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
