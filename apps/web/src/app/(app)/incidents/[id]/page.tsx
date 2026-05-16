import { serverFetch } from "@/lib/server-api";
import { notFound } from "next/navigation";
import Link from "next/link";

interface IncidentDetail {
  id: number;
  dataset_id: string;
  column: string | null;
  detector: string;
  severity: string;
  message: string;
  status: string;
  opened_at: string | null;
  opened_ago: string;
  resolved_at: string | null;
}

function SeverityBadge({ severity }: { severity: string }) {
  const s =
    severity === "fail"
      ? { bg: "var(--fail-bg)", color: "var(--fail)" }
      : { bg: "rgba(217,181,102,0.12)", color: "var(--warn)" };
  return (
    <span
      className="t-micro px-2 py-0.5"
      style={{ background: s.bg, color: s.color, fontFamily: "var(--font-jetbrains-mono)" }}
    >
      {severity.toUpperCase()}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const color =
    status === "open" ? "var(--fail)" : status === "resolved" ? "var(--pass)" : "var(--fg-3)";
  return (
    <span className="t-micro px-2 py-0.5 border" style={{ borderColor: color, color }}>
      {status}
    </span>
  );
}

export default async function IncidentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const incident = await serverFetch<IncidentDetail>(`/incidents/${id}`, 15);
  if (!incident) notFound();

  const yamlDef = `check: ${incident.detector}
dataset: ${incident.dataset_id}${incident.column ? `\ncolumn: ${incident.column}` : ""}
threshold:
  warn: 0.02
  fail: 0.10
baseline: 14d`;

  return (
    <div className="p-6 fade-in">
      {/* breadcrumb */}
      <div className="flex items-center gap-2 mb-4">
        <Link
          href="/incidents"
          className="flex items-center gap-1.5 t-small hover:opacity-80 transition-colors"
          style={{ color: "var(--accent)", fontFamily: "var(--font-jetbrains-mono)" }}
        >
          <span style={{ fontSize: 14, lineHeight: 1 }}>←</span>
          <span>Incidents</span>
        </Link>
        <span style={{ color: "var(--fg-3)", fontSize: 12 }}>/</span>
        <span className="t-small font-mono" style={{ color: "var(--fg-2)" }}>#{incident.id}</span>
      </div>

      {/* header */}
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <SeverityBadge severity={incident.severity} />
            <StatusBadge status={incident.status} />
            <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>{incident.detector}</span>
          </div>
          <h1 className="t-h1 font-mono mb-1" style={{ color: "var(--fg-0)" }}>
            {incident.dataset_id}
            {incident.column && <span style={{ color: "var(--fg-3)" }}>.{incident.column}</span>}
          </h1>
          <p className="t-body" style={{ color: "var(--fg-2)" }}>{incident.message}</p>
        </div>
      </div>

      {/* KPI band */}
      <div
        className="grid grid-cols-4 gap-px border border-line mb-8"
        style={{ background: "var(--line)" }}
      >
        {[
          { label: "Incident ID", value: `#${incident.id}` },
          { label: "Severity", value: incident.severity },
          { label: "Status", value: incident.status },
          { label: "Opened", value: incident.opened_ago },
        ].map((k) => (
          <div key={k.label} className="px-5 py-4" style={{ background: "var(--bg-1)" }}>
            <p className="kpi-label mb-1" style={{ color: "var(--fg-2)" }}>{k.label}</p>
            <p
              className="text-xl font-light font-mono"
              style={{
                color:
                  k.label === "Severity"
                    ? incident.severity === "fail" ? "var(--fail)" : "var(--warn)"
                    : k.label === "Status" && incident.status === "open"
                    ? "var(--fail)"
                    : "var(--fg-0)",
                fontFamily: "var(--font-jetbrains-mono)",
              }}
            >
              {k.value}
            </p>
          </div>
        ))}
      </div>

      <div className="flex gap-6" style={{ alignItems: "flex-start" }}>
        {/* main */}
        <div className="flex-1 min-w-0 space-y-5">
          {/* statistical evidence */}
          <div className="border border-line" style={{ background: "var(--bg-1)" }}>
            <div
              className="px-4 py-3 border-b border-line t-micro"
              style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}
            >
              Statistical evidence
            </div>
            <div className="p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="t-small" style={{ color: "var(--fg-1)" }}>Detector</span>
                <span className="t-small font-mono" style={{ color: "var(--fg-0)" }}>{incident.detector}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="t-small" style={{ color: "var(--fg-1)" }}>Dataset</span>
                <Link
                  href={`/datasets/${incident.dataset_id}`}
                  className="t-small font-mono hover:underline"
                  style={{ color: "var(--accent)" }}
                >
                  {incident.dataset_id}
                </Link>
              </div>
              {incident.column && (
                <div className="flex items-center justify-between">
                  <span className="t-small" style={{ color: "var(--fg-1)" }}>Column</span>
                  <Link
                    href={`/datasets/${incident.dataset_id}/${encodeURIComponent(incident.column)}`}
                    className="t-small font-mono hover:underline"
                    style={{ color: "var(--accent)" }}
                  >
                    {incident.column}
                  </Link>
                </div>
              )}
              <div className="flex items-center justify-between">
                <span className="t-small" style={{ color: "var(--fg-1)" }}>Verdict</span>
                <span
                  className="t-small font-mono"
                  style={{ color: incident.severity === "fail" ? "var(--fail)" : "var(--warn)" }}
                >
                  {incident.severity}
                </span>
              </div>
            </div>
          </div>

          {/* causal trace placeholder */}
          <div className="border border-line" style={{ background: "var(--bg-1)" }}>
            <div
              className="px-4 py-3 border-b border-line t-micro"
              style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}
            >
              Causal trace
            </div>
            <div className="px-4 py-8 text-center">
              <p className="t-small" style={{ color: "var(--fg-3)" }}>
                Causal attribution available in v1.3 — requires confirmed metric DAG.
              </p>
            </div>
          </div>

          {/* activity log */}
          <div className="border border-line" style={{ background: "var(--bg-1)" }}>
            <div
              className="px-4 py-3 border-b border-line t-micro"
              style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}
            >
              Activity
            </div>
            <div className="p-4 space-y-3">
              <div className="flex items-start gap-3">
                <span
                  style={{
                    display: "inline-block",
                    width: 6,
                    height: 6,
                    background: incident.severity === "fail" ? "var(--fail)" : "var(--warn)",
                    marginTop: 4,
                    flexShrink: 0,
                  }}
                />
                <div>
                  <p className="t-small" style={{ color: "var(--fg-1)" }}>
                    Incident opened — {incident.severity}
                  </p>
                  <p className="t-micro mt-0.5" style={{ color: "var(--fg-3)" }}>{incident.opened_ago}</p>
                </div>
              </div>
              {incident.resolved_at && (
                <div className="flex items-start gap-3">
                  <span
                    style={{
                      display: "inline-block",
                      width: 6,
                      height: 6,
                      background: "var(--pass)",
                      marginTop: 4,
                      flexShrink: 0,
                    }}
                  />
                  <div>
                    <p className="t-small" style={{ color: "var(--fg-1)" }}>Incident resolved</p>
                    <p className="t-micro mt-0.5" style={{ color: "var(--fg-3)" }}>auto-resolved after 3 consecutive passes</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* right rail */}
        <div style={{ width: 340, flexShrink: 0 }} className="space-y-4">
          <div className="border border-line" style={{ background: "var(--bg-1)" }}>
            <div
              className="px-4 py-3 border-b border-line t-micro"
              style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}
            >
              Rule definition
            </div>
            <pre
              className="p-4 t-micro overflow-x-auto"
              style={{
                color: "var(--fg-1)",
                fontFamily: "var(--font-jetbrains-mono)",
                lineHeight: 1.7,
                background: "var(--bg-2)",
                margin: 0,
              }}
            >
              {yamlDef}
            </pre>
          </div>

          <div className="border border-line" style={{ background: "var(--bg-1)" }}>
            <div
              className="px-4 py-3 border-b border-line t-micro"
              style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}
            >
              Links
            </div>
            <div className="divide-y divide-line">
              <Link
                href={`/datasets/${incident.dataset_id}`}
                className="flex items-center justify-between px-4 py-2.5 hover:bg-bg-2 transition-colors"
                style={{ color: "var(--fg-0)" }}
              >
                <span className="t-small">View dataset</span>
                <span style={{ color: "var(--accent)", fontSize: 12 }}>→</span>
              </Link>
              {incident.column && (
                <Link
                  href={`/datasets/${incident.dataset_id}/${encodeURIComponent(incident.column)}`}
                  className="flex items-center justify-between px-4 py-2.5 hover:bg-bg-2 transition-colors"
                  style={{ color: "var(--fg-0)" }}
                >
                  <span className="t-small">View column profile</span>
                  <span style={{ color: "var(--accent)", fontSize: 12 }}>→</span>
                </Link>
              )}
              <Link
                href="/tests"
                className="flex items-center justify-between px-4 py-2.5 hover:bg-bg-2 transition-colors"
                style={{ color: "var(--fg-0)" }}
              >
                <span className="t-small">View all tests</span>
                <span style={{ color: "var(--accent)", fontSize: 12 }}>→</span>
              </Link>
            </div>
          </div>

          {/* tasks */}
          <div className="border border-line" style={{ background: "var(--bg-1)" }}>
            <div
              className="px-4 py-3 border-b border-line t-micro flex items-center justify-between"
              style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}
            >
              <span>Tasks</span>
              <Link href="/tasks" className="t-micro" style={{ color: "var(--accent)", textTransform: "none", letterSpacing: 0 }}>
                View all
              </Link>
            </div>
            <div className="divide-y divide-line">
              {[
                { label: "Acknowledge", done: false },
                { label: "Investigate root cause", done: false },
                { label: "Mitigate", done: false },
                { label: "Write postmortem", done: false },
              ].map((t) => (
                <div key={t.label} className="flex items-center gap-3 px-4 py-2.5">
                  <div
                    style={{
                      width: 14,
                      height: 14,
                      border: "1px solid var(--line)",
                      background: t.done ? "var(--pass)" : "transparent",
                      flexShrink: 0,
                    }}
                  />
                  <span className="t-small" style={{ color: t.done ? "var(--fg-3)" : "var(--fg-1)", textDecoration: t.done ? "line-through" : "none" }}>
                    {t.label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
