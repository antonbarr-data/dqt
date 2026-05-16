import { serverFetch } from "@/lib/server-api";
import Link from "next/link";

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

interface Task {
  id: string;
  kind: "acknowledge" | "investigate" | "mitigate" | "postmortem" | "hitl";
  title: string;
  subtitle: string;
  incidentId: number | null;
  severity: string;
  due: string;
  assignee: string;
  done: boolean;
}

const HITL_TASKS: Task[] = [
  {
    id: "hitl-1",
    kind: "hitl",
    title: "Confirm: amount_usd → platform_fee_usd causal edge",
    subtitle: "Stability score 0.61 — below 0.70 threshold. Review proposed edge.",
    incidentId: null,
    severity: "warn",
    due: "today",
    assignee: "me",
    done: false,
  },
  {
    id: "hitl-2",
    kind: "hitl",
    title: "Review AI-suggested check: row_count_in_range on gig_vendor_stats",
    subtitle: "Confidence 0.88. Accept to add to test suite.",
    incidentId: null,
    severity: "warn",
    due: "today",
    assignee: "me",
    done: false,
  },
];

function kindLabel(kind: Task["kind"]): string {
  switch (kind) {
    case "acknowledge": return "Acknowledge";
    case "investigate": return "Investigate";
    case "mitigate": return "Mitigate";
    case "postmortem": return "Postmortem";
    case "hitl": return "HITL Review";
  }
}

function kindColor(kind: Task["kind"]): string {
  switch (kind) {
    case "acknowledge": return "var(--warn)";
    case "investigate": return "var(--accent)";
    case "mitigate": return "var(--fail)";
    case "postmortem": return "var(--fg-2)";
    case "hitl": return "var(--accent)";
  }
}

function severityStyle(severity: string): { bg: string; color: string } {
  if (severity === "fail") return { bg: "var(--fail-bg)", color: "var(--fail)" };
  if (severity === "warn") return { bg: "rgba(217,181,102,0.1)", color: "var(--warn)" };
  return { bg: "transparent", color: "var(--fg-3)" };
}

export default async function TasksPage() {
  const incidents = await serverFetch<IncidentRow[]>("/incidents?status=open", 15) ?? [];

  const incidentTasks: Task[] = incidents.flatMap((inc) => [
    {
      id: `ack-${inc.id}`,
      kind: "acknowledge" as const,
      title: `Acknowledge: ${inc.dataset_id}${inc.column ? `.${inc.column}` : ""}`,
      subtitle: inc.message,
      incidentId: inc.id,
      severity: inc.severity,
      due: "now",
      assignee: "me",
      done: false,
    },
    {
      id: `inv-${inc.id}`,
      kind: "investigate" as const,
      title: `Investigate: ${inc.detector} on ${inc.dataset_id}`,
      subtitle: `Opened ${inc.opened_ago}`,
      incidentId: inc.id,
      severity: inc.severity,
      due: "1h",
      assignee: "me",
      done: false,
    },
  ]);

  const allTasks = [...incidentTasks, ...HITL_TASKS];
  const openCount = allTasks.filter((t) => !t.done).length;
  const hitlCount = HITL_TASKS.filter((t) => !t.done).length;
  const incCount = incidentTasks.filter((t) => !t.done).length;

  const grouped: Record<string, Task[]> = {
    "Incidents": incidentTasks,
    "HITL Reviews": HITL_TASKS,
  };

  return (
    <div className="p-6 fade-in">
      <div className="flex items-baseline justify-between mb-6">
        <h1 className="t-h1" style={{ color: "var(--fg-0)" }}>Tasks</h1>
        <span className="t-small" style={{ color: "var(--fg-3)" }}>{openCount} open</span>
      </div>

      {/* KPI band */}
      <div
        className="grid grid-cols-4 gap-px border border-line mb-8"
        style={{ background: "var(--line)" }}
      >
        {[
          { label: "Open tasks", value: String(openCount), color: openCount > 0 ? "var(--warn)" : "var(--pass)" },
          { label: "Incident tasks", value: String(incCount), color: incCount > 0 ? "var(--fail)" : "var(--fg-0)" },
          { label: "HITL reviews", value: String(hitlCount), color: hitlCount > 0 ? "var(--accent)" : "var(--fg-0)" },
          { label: "Completed today", value: "0", color: "var(--fg-0)" },
        ].map((k) => (
          <div key={k.label} className="px-5 py-4" style={{ background: "var(--bg-1)" }}>
            <p className="kpi-label mb-1" style={{ color: "var(--fg-2)" }}>{k.label}</p>
            <p className="text-xl font-light font-mono" style={{ color: k.color, fontFamily: "var(--font-jetbrains-mono)" }}>
              {k.value}
            </p>
          </div>
        ))}
      </div>

      {/* task groups */}
      <div className="space-y-6">
        {Object.entries(grouped).map(([group, tasks]) => (
          <div key={group} className="border border-line" style={{ background: "var(--bg-1)" }}>
            <div
              className="px-4 py-2.5 border-b border-line flex items-center justify-between"
              style={{ background: "var(--bg-1)" }}
            >
              <span
                className="t-micro"
                style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}
              >
                {group}
              </span>
              <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>
                {tasks.filter((t) => !t.done).length} open
              </span>
            </div>

            {tasks.length === 0 ? (
              <div className="px-4 py-6 text-center t-small" style={{ color: "var(--fg-3)" }}>
                No tasks
              </div>
            ) : (
              <div className="divide-y divide-line">
                {tasks.map((task) => {
                  const ss = severityStyle(task.severity);
                  return (
                    <div
                      key={task.id}
                      className="flex items-start gap-4 px-4 py-3 transition-colors hover:bg-bg-2"
                      style={task.severity === "fail" && !task.done ? { background: "var(--fail-bg)" } : undefined}
                    >
                      {/* checkbox */}
                      <div
                        style={{
                          width: 16,
                          height: 16,
                          border: "1px solid var(--line)",
                          background: task.done ? "var(--pass)" : "transparent",
                          flexShrink: 0,
                          marginTop: 2,
                        }}
                      />

                      {/* content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                          <span
                            className="t-micro px-1.5 py-0.5"
                            style={{
                              background: "transparent",
                              color: kindColor(task.kind),
                              border: `1px solid ${kindColor(task.kind)}`,
                              fontFamily: "var(--font-jetbrains-mono)",
                            }}
                          >
                            {kindLabel(task.kind)}
                          </span>
                          {task.severity !== "pass" && (
                            <span
                              className="t-micro px-1.5 py-0.5"
                              style={{ background: ss.bg, color: ss.color, fontFamily: "var(--font-jetbrains-mono)" }}
                            >
                              {task.severity}
                            </span>
                          )}
                        </div>
                        <p className="t-small" style={{ color: task.done ? "var(--fg-3)" : "var(--fg-0)", textDecoration: task.done ? "line-through" : "none" }}>
                          {task.title}
                        </p>
                        <p className="t-micro mt-0.5" style={{ color: "var(--fg-3)" }}>{task.subtitle}</p>
                      </div>

                      {/* meta */}
                      <div className="flex items-center gap-3 flex-shrink-0">
                        <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>due: {task.due}</span>
                        {task.incidentId && (
                          <Link
                            href={`/incidents/${task.incidentId}`}
                            className="t-micro px-2 py-0.5 border border-line hover:border-accent transition-colors"
                            style={{ color: "var(--fg-2)", fontFamily: "var(--font-jetbrains-mono)" }}
                          >
                            #{task.incidentId}
                          </Link>
                        )}
                        {task.kind === "hitl" && (
                          <Link
                            href="/causality"
                            className="t-micro px-2 py-0.5 border transition-colors"
                            style={{ borderColor: "var(--accent)", color: "var(--accent)" }}
                          >
                            Review →
                          </Link>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
