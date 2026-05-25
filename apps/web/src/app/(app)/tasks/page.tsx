import { serverFetch } from "@/lib/server-api";

interface OncallStatus {
  current_oncall: { email: string; name: string | null } | null;
  upcoming_oncall: { email: string; name: string | null } | null;
}

interface CheckItem {
  id: string;
  dataset_id: string;
  column: string | null;
  detector: string;
  verdict: string;
  score: number | null;
  ran_at: string | null;
  ran_at_ago: string | null;
  plain_english: string | null;
}

interface Task {
  id: string;
  kind: "investigate" | "review" | "hitl";
  title: string;
  subtitle: string;
  severity: string;
  due: string;
  assignee: string;
  done: boolean;
}

const HITL_TASKS: Task[] = [];

function kindLabel(kind: Task["kind"]): string {
  switch (kind) {
    case "investigate": return "Investigate";
    case "review": return "Review";
    case "hitl": return "HITL Review";
  }
}

function kindColor(kind: Task["kind"]): string {
  switch (kind) {
    case "investigate": return "var(--fail)";
    case "review": return "var(--warn)";
    case "hitl": return "var(--accent)";
  }
}

function severityStyle(severity: string): { bg: string; color: string } {
  if (severity === "fail") return { bg: "var(--fail-bg)", color: "var(--fail)" };
  if (severity === "warn") return { bg: "rgba(217,181,102,0.1)", color: "var(--warn)" };
  return { bg: "transparent", color: "var(--fg-3)" };
}

export default async function TasksPage() {
  const [checks, oncall] = await Promise.all([
    serverFetch<CheckItem[]>("/checks", 15) ?? [],
    serverFetch<OncallStatus>("/oncall/status", 15),
  ]);
  const oncallPerson = oncall?.current_oncall ?? oncall?.upcoming_oncall;
  const assignee = oncallPerson
    ? (oncallPerson.name ?? oncallPerson.email)
    : "on-call";
  const alertChecks = (checks as CheckItem[]).filter((c) => c.verdict === "fail" || c.verdict === "warn");

  const checkTasks: Task[] = alertChecks.map((c) => ({
    id: `check-${c.id}`,
    kind: c.verdict === "fail" ? "investigate" : "review",
    title: `${c.verdict === "fail" ? "Investigate" : "Review"}: ${c.dataset_id}${c.column ? `.${c.column}` : ""} — ${c.detector}`,
    subtitle: c.plain_english ?? (c.ran_at_ago ? `Last run ${c.ran_at_ago}` : "Not yet run"),
    severity: c.verdict,
    due: c.verdict === "fail" ? "now" : "4h",
    assignee,
    done: false,
  }));

  const allTasks = [...checkTasks, ...HITL_TASKS];
  const openCount = allTasks.filter((t) => !t.done).length;
  const failCount = checkTasks.filter((t) => t.severity === "fail").length;
  const warnCount = checkTasks.filter((t) => t.severity === "warn").length;
  const hitlCount = HITL_TASKS.filter((t) => !t.done).length;

  const grouped: Record<string, Task[]> = {
    "Check alerts": checkTasks,
    "HITL reviews": HITL_TASKS,
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
          { label: "Failures", value: String(failCount), color: failCount > 0 ? "var(--fail)" : "var(--fg-0)" },
          { label: "Warnings", value: String(warnCount), color: warnCount > 0 ? "var(--warn)" : "var(--fg-0)" },
          { label: "HITL reviews", value: String(hitlCount), color: hitlCount > 0 ? "var(--accent)" : "var(--fg-0)" },
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

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                          <span
                            className="t-micro px-1.5 py-0.5"
                            style={{
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

                      <div className="flex items-center gap-3 flex-shrink-0">
                        <span className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>due: {task.due}</span>
                        <span className="t-micro px-1.5 py-0.5 border border-line font-mono" style={{ color: "var(--fg-3)" }}>
                          {task.assignee}
                        </span>
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
