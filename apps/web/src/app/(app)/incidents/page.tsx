import { serverFetch } from "@/lib/server-api";
import Link from "next/link";
import { IncidentTableRow } from "./incident-row";

interface IncidentRow {
  id: number;
  dataset_id: string;
  column: string | null;
  detector: string;
  severity: string;
  message: string;
  status: string;
  opened_ago: string;
}

export default async function IncidentsPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string }>;
}) {
  const { status = "open" } = await searchParams;

  let open: IncidentRow[] | null = null;
  let all: IncidentRow[] | null = null;
  let fetchError: string | null = null;

  try {
    [open, all] = await Promise.all([
      serverFetch<IncidentRow[]>(`/incidents?status=open`, 15),
      serverFetch<IncidentRow[]>(`/incidents?status=${status}`, 15),
    ]);
  } catch {
    fetchError = "Failed to load incidents.";
  }

  const incidents = all ?? [];
  const openCount = open?.length ?? 0;
  const failCount = incidents.filter((i) => i.severity === "fail").length;
  const warnCount = incidents.filter((i) => i.severity === "warn").length;

  return (
    <div className="p-6 fade-in">
      <div className="flex items-baseline justify-between mb-6">
        <h1 className="t-h1" style={{ color: "var(--fg-0)" }}>Incidents</h1>
        <span className="t-small" style={{ color: "var(--fg-3)" }}>
          {incidents.length} {status}
        </span>
      </div>

      {/* KPI band */}
      <div
        className="grid grid-cols-4 gap-px border border-line mb-6"
        style={{ background: "var(--line)" }}
      >
        {[
          { label: "Open", value: String(openCount), color: openCount > 0 ? "var(--fail)" : "var(--pass)" },
          { label: "Failing", value: String(failCount), color: failCount > 0 ? "var(--fail)" : "var(--fg-0)" },
          { label: "Warning", value: String(warnCount), color: warnCount > 0 ? "var(--warn)" : "var(--fg-0)" },
          { label: "Auto-explained", value: "0", color: "var(--fg-0)" },
        ].map((k) => (
          <div key={k.label} className="px-5 py-4" style={{ background: "var(--bg-1)" }}>
            <p className="kpi-label mb-1" style={{ color: "var(--fg-2)" }}>{k.label}</p>
            <p className="text-xl font-light font-mono" style={{ color: k.color, fontFamily: "var(--font-jetbrains-mono)" }}>
              {k.value}
            </p>
          </div>
        ))}
      </div>

      {/* filter bar */}
      <div className="flex items-center gap-2 mb-5">
        {["open", "resolved", "all"].map((s) => (
          <Link
            key={s}
            href={s === "all" ? "/incidents?status=open" : `/incidents?status=${s}`}
            className="t-small px-2.5 py-1 border transition-colors"
            style={{
              borderColor: status === s || (s === "open" && !status) ? "var(--accent)" : "var(--line)",
              color: status === s || (s === "open" && !status) ? "var(--accent)" : "var(--fg-2)",
              background: status === s ? "var(--accent-bg)" : "transparent",
            }}
          >
            {s}
          </Link>
        ))}
      </div>

      {/* error state */}
      {fetchError && (
        <div className="border border-line p-8 text-center" style={{ background: "var(--bg-1)" }}>
          <p className="t-small" style={{ color: "var(--fail)" }}>{fetchError}</p>
        </div>
      )}

      {/* table */}
      {!fetchError && (
        <div className="border border-line" style={{ background: "var(--bg-1)" }}>
          {incidents.length === 0 ? (
            <div className="px-4 py-12 text-center t-small" style={{ color: "var(--fg-3)" }}>
              No {status} incidents
            </div>
          ) : (
            <table className="w-full" style={{ borderCollapse: "collapse" }}>
              <thead>
                <tr className="border-b border-line">
                  {["", "Severity", "Dataset", "Column", "Detector", "Message", "Opened"].map((h) => (
                    <th
                      key={h}
                      className="px-3 py-2 text-left t-micro"
                      style={{ color: "var(--fg-2)", fontWeight: 400, letterSpacing: "0.08em", textTransform: "uppercase" }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {incidents.map((inc) => (
                  <IncidentTableRow key={inc.id} inc={inc} />
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
