"use client";

interface Incident {
  id: number;
  detector_slug: string;
  severity: string;
  message: string;
  status: string;
  opened_at: string;
  resolved_at: string | null;
}

const SEVERITY_COLOR: Record<string, string> = {
  critical: "var(--fail)",
  high: "var(--fail)",
  medium: "var(--warn)",
  low: "var(--fg-3)",
  info: "var(--accent)",
};

function fmtDate(ts: string): string {
  const d = new Date(ts);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function IncidentsPanel({ incidents }: { incidents: Incident[] }) {
  const open = incidents.filter(i => i.status === "open");
  const closed = incidents.filter(i => i.status !== "open");

  return (
    <div className="border border-line" style={{ background: "var(--bg-1)" }}>
      <div className="px-4 py-2.5 border-b border-line flex items-center justify-between">
        <span className="t-micro" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
          Incidents
        </span>
        {open.length > 0 && (
          <span className="t-micro px-1.5 py-0.5" style={{
            background: "var(--fail-bg)", color: "var(--fail)",
            border: "1px solid var(--line)", fontFamily: "var(--font-jetbrains-mono)",
          }}>
            {open.length} open
          </span>
        )}
      </div>

      {incidents.length === 0 ? (
        <div className="px-4 py-4 t-small" style={{ color: "var(--fg-3)" }}>No incidents.</div>
      ) : (
        <div>
          {incidents.map(inc => (
            <div
              key={inc.id}
              className="px-4 py-2.5 border-b border-line last:border-0"
              style={{ background: inc.status === "open" ? "var(--fail-bg)" : undefined }}
            >
              <div className="flex items-center justify-between gap-2 mb-0.5">
                <div className="flex items-center gap-2 min-w-0">
                  <div style={{
                    width: 6, height: 6, borderRadius: "50%",
                    background: SEVERITY_COLOR[inc.severity] ?? "var(--fg-3)",
                    flexShrink: 0,
                  }} />
                  <span className="t-small font-mono truncate" style={{
                    color: "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)",
                  }}>
                    {inc.detector_slug}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <span className="t-micro" style={{ color: "var(--fg-3)" }}>{fmtDate(inc.opened_at)}</span>
                  <span className="t-micro px-1.5 py-0.5" style={{
                    background: inc.status === "open" ? "rgba(217,100,100,0.15)" : "var(--bg-2)",
                    color: inc.status === "open" ? "var(--fail)" : "var(--fg-3)",
                    border: "1px solid var(--line)",
                  }}>
                    {inc.status}
                  </span>
                </div>
              </div>
              <p className="t-small" style={{ color: "var(--fg-2)", lineHeight: 1.4 }}>{inc.message}</p>
              {inc.resolved_at && (
                <p className="t-micro mt-0.5" style={{ color: "var(--fg-3)" }}>
                  resolved {fmtDate(inc.resolved_at)}
                </p>
              )}
            </div>
          ))}
          {closed.length > 0 && (
            <div className="px-4 py-2 border-t border-line">
              <span className="t-micro" style={{ color: "var(--fg-3)" }}>
                {closed.length} resolved
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
