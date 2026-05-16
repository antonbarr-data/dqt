import Link from "next/link";

const MOCK_DATASETS = [
  { id: "marketing_campaigns", source: "gigler_warehouse", rows: "2.4M", columns: 16, checks: 8, status: "pass", lastRun: "2 min ago" },
  { id: "gigler_transactions", source: "gigler_warehouse", rows: "8.1M", columns: 16, checks: 12, status: "fail", lastRun: "2 min ago" },
  { id: "gig_prices", source: "gigler_warehouse", rows: "1.2M", columns: 9, checks: 5, status: "warn", lastRun: "2 min ago" },
  { id: "gig_vendor_stats", source: "gigler_warehouse", rows: "980K", columns: 11, checks: 5, status: "pass", lastRun: "5 min ago" },
  { id: "fct_orders", source: "demo_warehouse", rows: "5.3M", columns: 14, checks: 10, status: "pass", lastRun: "10 min ago" },
  { id: "fct_sessions", source: "demo_warehouse", rows: "12.1M", columns: 8, checks: 6, status: "warn", lastRun: "10 min ago" },
];

type Status = "pass" | "warn" | "fail";

function StatusDot({ status }: { status: Status }) {
  const color = status === "pass" ? "var(--pass)" : status === "warn" ? "var(--warn)" : "var(--fail)";
  return (
    <span
      style={{
        display: "inline-block",
        width: 8,
        height: 8,
        background: color,
        boxShadow: `0 0 0 2px ${color}30`,
        flexShrink: 0,
      }}
    />
  );
}

export default function DatasetsPage() {
  return (
    <div className="p-6">
      {/* page header */}
      <div className="flex items-center justify-between mb-5">
        <h1 className="t-h1" style={{ color: "var(--fg-0)" }}>Datasets</h1>
        <div className="t-small" style={{ color: "var(--fg-2)" }}>
          {MOCK_DATASETS.length} datasets
        </div>
      </div>

      {/* table */}
      <div className="border border-line" style={{ background: "var(--bg-1)" }}>
        <table className="w-full" style={{ borderCollapse: "collapse" }}>
          <thead>
            <tr className="border-b border-line">
              {["Dataset", "Source", "Rows", "Columns", "Tests", "Status", "Last Run"].map((h) => (
                <th
                  key={h}
                  className="px-3 py-2 text-left t-micro"
                  style={{
                    color: "var(--fg-2)",
                    fontWeight: 400,
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {MOCK_DATASETS.map((ds) => (
              <tr
                key={ds.id}
                className="border-b border-line last:border-0 hover:bg-bg-2 transition-colors"
              >
                <td className="px-3 py-2">
                  <Link
                    href={`/datasets/${ds.id}`}
                    className="t-body font-mono hover:underline"
                    style={{ color: "var(--fg-0)" }}
                  >
                    {ds.id}
                  </Link>
                </td>
                <td className="px-3 py-2 t-small" style={{ color: "var(--fg-1)" }}>
                  {ds.source}
                </td>
                <td className="px-3 py-2 t-small font-mono" style={{ color: "var(--fg-1)" }}>
                  {ds.rows}
                </td>
                <td className="px-3 py-2 t-small font-mono" style={{ color: "var(--fg-1)" }}>
                  {ds.columns}
                </td>
                <td className="px-3 py-2 t-small font-mono" style={{ color: "var(--fg-1)" }}>
                  {ds.checks}
                </td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-1.5">
                    <StatusDot status={ds.status as Status} />
                    <span
                      className="t-small"
                      style={{
                        color:
                          ds.status === "pass"
                            ? "var(--pass)"
                            : ds.status === "warn"
                            ? "var(--warn)"
                            : "var(--fail)",
                      }}
                    >
                      {ds.status}
                    </span>
                  </div>
                </td>
                <td className="px-3 py-2 t-small" style={{ color: "var(--fg-2)" }}>
                  {ds.lastRun}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
