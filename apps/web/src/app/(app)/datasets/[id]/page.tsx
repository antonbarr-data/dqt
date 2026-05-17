import { serverFetch } from "@/lib/server-api";
import { notFound } from "next/navigation";
import Link from "next/link";

interface CheckResult {
  id: number;
  dataset_id: string;
  column: string | null;
  detector: string;
  score: number | null;
  verdict: string | null;
  message: string | null;
  details: Record<string, unknown> | null;
  ran_at_ago: string;
}

interface DatasetDetail {
  id: string;
  source: string;
  schema: string;
  row_count: number | null;
  column_count: number | null;
  check_count: number;
  status: string;
  last_run: string;
  checks: CheckResult[];
}

type Verdict = "pass" | "warn" | "fail" | "unknown";

function VerdictBadge({ verdict }: { verdict: Verdict }) {
  const styles: Record<string, { bg: string; color: string }> = {
    pass: { bg: "var(--pass-bg, #0d2a1a)", color: "var(--pass)" },
    warn: { bg: "var(--warn-bg, #2a1f00)", color: "var(--warn)" },
    fail: { bg: "var(--fail-bg)", color: "var(--fail)" },
    unknown: { bg: "var(--bg-2)", color: "var(--fg-3)" },
  };
  const s = styles[verdict] ?? styles.unknown;
  return (
    <span
      className="t-micro px-1.5 py-0.5"
      style={{ background: s.bg, color: s.color, fontFamily: "var(--font-jetbrains-mono)" }}
    >
      {verdict}
    </span>
  );
}

function fmtRows(n: number | null): string {
  if (n === null) return "--";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

export default async function DatasetDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ filter?: string }>;
}) {
  const { id } = await params;
  const { filter } = await searchParams;
  const dataset = await serverFetch<DatasetDetail>(`/datasets/${encodeURIComponent(id)}`, 30);

  if (!dataset) notFound();

  const failCount = dataset.checks.filter((c) => c.verdict === "fail").length;
  const warnCount = dataset.checks.filter((c) => c.verdict === "warn").length;
  const passCount = dataset.checks.filter((c) => c.verdict === "pass").length;

  const visibleChecks = filter
    ? dataset.checks.filter((c) => c.verdict === filter)
    : dataset.checks;

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <Link href="/datasets" className="flex items-center gap-1.5 t-small transition-colors hover:opacity-80" style={{ color: "var(--accent)", fontFamily: "var(--font-jetbrains-mono)" }}>
          <span style={{ fontSize: 14, lineHeight: 1 }}>&#8592;</span>
          <span>Datasets</span>
        </Link>
        <span style={{ color: "var(--fg-3)", fontSize: 12 }}>/</span>
        <span className="t-small font-mono" style={{ color: "var(--fg-2)" }}>{dataset.id}</span>
      </div>
      <div className="flex items-baseline gap-4 mb-6">
        <h1 className="t-h1 font-mono" style={{ color: "var(--fg-0)" }}>
          {dataset.id}
        </h1>
        <span className="t-small" style={{ color: "var(--fg-3)" }}>
          {dataset.source} / {dataset.schema}
        </span>
      </div>

      {/* KPI band */}
      <div
        className="grid grid-cols-4 gap-px border border-line mb-8"
        style={{ background: "var(--line)" }}
      >
        {[
          { label: "Rows", value: fmtRows(dataset.row_count) },
          { label: "Columns", value: String(dataset.column_count ?? "--") },
          { label: "Checks", value: String(dataset.check_count) },
          { label: "Last run", value: dataset.last_run },
        ].map((k) => (
          <div key={k.label} className="px-5 py-4" style={{ background: "var(--bg-1)" }}>
            <p className="kpi-label mb-1" style={{ color: "var(--fg-2)" }}>
              {k.label}
            </p>
            <p
              className="text-xl font-light font-mono"
              style={{ color: "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)" }}
            >
              {k.value}
            </p>
          </div>
        ))}
      </div>

      {/* Status summary + filter */}
      <div className="flex items-center gap-2 mb-5">
        <Link
          href={filter === "pass" ? `/datasets/${id}` : `/datasets/${id}?filter=pass`}
          className="t-small px-2 py-0.5 border transition-colors"
          style={{
            color: "var(--pass)",
            borderColor: filter === "pass" ? "var(--pass)" : "var(--line)",
            background: filter === "pass" ? "rgba(127,179,148,0.1)" : "transparent",
          }}
        >
          {passCount} pass
        </Link>
        <Link
          href={filter === "warn" ? `/datasets/${id}` : `/datasets/${id}?filter=warn`}
          className="t-small px-2 py-0.5 border transition-colors"
          style={{
            color: "var(--warn)",
            borderColor: filter === "warn" ? "var(--warn)" : "var(--line)",
            background: filter === "warn" ? "rgba(217,181,102,0.1)" : "transparent",
          }}
        >
          {warnCount} warn
        </Link>
        <Link
          href={filter === "fail" ? `/datasets/${id}` : `/datasets/${id}?filter=fail`}
          className="t-small px-2 py-0.5 border transition-colors"
          style={{
            color: "var(--fail)",
            borderColor: filter === "fail" ? "var(--fail)" : "var(--line)",
            background: filter === "fail" ? "var(--fail-bg)" : "transparent",
          }}
        >
          {failCount} fail
        </Link>
        {filter && (
          <Link
            href={`/datasets/${id}`}
            className="t-micro px-1.5 py-0.5 border border-line transition-colors hover:bg-bg-2"
            style={{ color: "var(--fg-3)" }}
          >
            clear
          </Link>
        )}
      </div>

      {/* Column checks table */}
      <div className="border border-line" style={{ background: "var(--bg-1)" }}>
        <div
          className="px-3 py-2 border-b border-line t-micro"
          style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}
        >
          Null fraction by column
        </div>
        <table className="w-full" style={{ borderCollapse: "collapse" }}>
          <thead>
            <tr className="border-b border-line">
              {["Column", "Verdict", "Null fraction", "Null / Total", "Tested"].map((h) => (
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
            {visibleChecks.length === 0 ? (
              <tr>
                <td
                  colSpan={5}
                  className="px-3 py-4 t-small text-center"
                  style={{ color: "var(--fg-3)" }}
                >
                  {filter ? `No ${filter} checks.` : "No checks yet."}
                </td>
              </tr>
            ) : (
              visibleChecks.map((chk) => {
                const d = chk.details ?? {};
                const nullCount = (d.null_count as number) ?? null;
                const total = (d.total_count as number) ?? null;
                const frac = chk.score !== null ? (chk.score * 100).toFixed(2) + "%" : "--";
                const colHref = chk.column ? `/datasets/${dataset.id}/${encodeURIComponent(chk.column)}` : null;
                return (
                  <tr
                    key={chk.id}
                    className="border-b border-line last:border-0 hover:bg-bg-2 transition-colors"
                    style={chk.verdict === "fail" ? { background: "var(--fail-bg)" } : undefined}
                  >
                    <td className="px-3 py-2 t-small font-mono" style={{ color: "var(--fg-0)" }}>
                      {colHref ? (
                        <Link href={colHref as never} className="hover:underline" style={{ color: "var(--accent)" }}>
                          {chk.column}
                        </Link>
                      ) : (
                        <span style={{ color: "var(--fg-3)" }}>(table)</span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <VerdictBadge verdict={(chk.verdict ?? "unknown") as Verdict} />
                    </td>
                    <td
                      className="px-3 py-2 t-small font-mono"
                      style={{ color: chk.verdict === "fail" ? "var(--fail)" : chk.verdict === "warn" ? "var(--warn)" : "var(--fg-1)" }}
                    >
                      {frac}
                    </td>
                    <td className="px-3 py-2 t-small font-mono" style={{ color: "var(--fg-2)" }}>
                      {nullCount !== null && total !== null
                        ? `${nullCount.toLocaleString()} / ${total.toLocaleString()}`
                        : "--"}
                    </td>
                    <td className="px-3 py-2 t-small" style={{ color: "var(--fg-3)" }}>
                      {chk.ran_at_ago}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
