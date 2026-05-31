"use client";

interface ColumnStats {
  data_type: string | null;
  nullable: boolean | null;
  position: number | null;
  kind: string;
}

interface SchemaVersion {
  id: number;
  data_type: string | null;
  nullable: boolean | null;
  position: number | null;
  recorded_at: string;
}

function fmtDate(ts: string): string {
  const d = new Date(ts);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function NullableBadge({ nullable }: { nullable: boolean | null }) {
  if (nullable === null) return <span className="t-micro" style={{ color: "var(--fg-3)" }}>--</span>;
  return (
    <span className="t-micro px-1.5 py-0.5" style={{
      background: nullable ? "rgba(217,181,102,0.1)" : "rgba(127,179,148,0.1)",
      color: nullable ? "var(--warn)" : "var(--pass)",
      border: "1px solid var(--line)",
      fontFamily: "var(--font-jetbrains-mono)",
    }}>
      {nullable ? "NULLABLE" : "NOT NULL"}
    </span>
  );
}

export function SchemaPanel({
  stats,
  schemaHistory,
}: {
  stats: ColumnStats | null;
  schemaHistory: SchemaVersion[];
}) {
  return (
    <div className="border border-line" style={{ background: "var(--bg-1)" }}>
      <div className="px-4 py-2.5 border-b border-line flex items-center justify-between">
        <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
          Schema
        </span>
        {schemaHistory.length > 1 && (
          <span className="t-micro font-mono" style={{ color: "var(--warn)", fontFamily: "var(--font-jetbrains-mono)" }}>
            {schemaHistory.length} versions
          </span>
        )}
      </div>

      {/* Current schema */}
      <div className="px-4 py-3 border-b border-line">
        <div className="flex items-center gap-3 flex-wrap">
          {stats?.data_type && (
            <span className="t-small font-mono" style={{ color: "var(--accent)", fontFamily: "var(--font-jetbrains-mono)" }}>
              {stats.data_type}
            </span>
          )}
          <NullableBadge nullable={stats?.nullable ?? null} />
          {stats?.position !== null && stats?.position !== undefined && (
            <span className="t-micro" style={{ color: "var(--fg-3)" }}>position {stats.position}</span>
          )}
          {stats?.kind && (
            <span className="t-micro" style={{ color: "var(--fg-3)" }}>{stats.kind}</span>
          )}
        </div>
      </div>

      {/* Version history */}
      {schemaHistory.length === 0 ? (
        <div className="px-4 py-3 t-small" style={{ color: "var(--fg-3)" }}>No schema changes recorded.</div>
      ) : (
        <div>
          {schemaHistory.map((v, i) => {
            const isLatest = i === schemaHistory.length - 1;
            return (
              <div
                key={v.id}
                className="px-4 py-2.5 border-b border-line last:border-0 flex items-start gap-3"
              >
                {/* Timeline dot */}
                <div className="flex flex-col items-center flex-shrink-0 mt-0.5">
                  <div style={{
                    width: 7, height: 7, borderRadius: "50%",
                    background: isLatest ? "var(--accent)" : "var(--fg-3)",
                    flexShrink: 0,
                  }} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="t-small font-mono" style={{ color: "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)" }}>
                      {v.data_type ?? "unknown"}
                    </span>
                    <NullableBadge nullable={v.nullable} />
                    {v.position !== null && (
                      <span className="t-micro" style={{ color: "var(--fg-3)" }}>pos {v.position}</span>
                    )}
                  </div>
                  <p className="t-micro mt-0.5" style={{ color: "var(--fg-3)" }}>{fmtDate(v.recorded_at)}</p>
                </div>
                {isLatest && (
                  <span className="t-micro px-1.5 py-0.5 flex-shrink-0" style={{
                    background: "rgba(127,179,148,0.1)", color: "var(--pass)",
                    border: "1px solid var(--line)",
                  }}>
                    current
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
