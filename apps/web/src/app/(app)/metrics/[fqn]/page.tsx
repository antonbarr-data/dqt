import { Suspense } from "react";
import { serverFetch } from "@/lib/server-api";
import { notFound } from "next/navigation";
import Link from "next/link";
import { InsightClient } from "./insight-client";
import { SubscribeButton } from "@/components/subscriptions/subscribe-button";
import { MetricProfilePanel } from "./metric-profile-panel";
import { SeasonalityChart } from "./seasonality-chart";

interface MetricDetail {
  fqn: string;
  display_name: string;
  kind: string;
  dataset: string;
  description: string;
  owners: string[];
  tags: string[];
  unit: string;
  warn_threshold: number | null;
  fail_threshold: number | null;
  current_value: number | null;
  current_verdict: string | null;
  last_run: string | null;
  pinned: boolean;
  grain: string | null;
  additivity: string | null;
  good_direction: string | null;
  refresh_cadence: string | null;
  lineage: { label: string; kind?: string }[];
  source_id: string | null;
  expr_type: string | null;
  expr_sql: string | null;
  numerator_sql: string | null;
  denominator_sql: string | null;
  filter_sql: string | null;
}

interface MetricProfile {
  mean: number;
  median: number;
  stddev: number;
  min: number;
  max: number;
  p25: number;
  p75: number;
  cv: number;
  trailing_13w_mean: number;
  count: number;
  null_rate: number;
  histogram: { x: number; count: number }[];
  seasonality: { day: string; avg: number }[];
  known_data_issues: { detector: string; column: string | null; verdict: string; message: string; ran_at: string | null }[];
}

function fmt(v: number): string {
  if (Math.abs(v) >= 1000) return v.toLocaleString(undefined, { maximumFractionDigits: 1 });
  if (Math.abs(v) >= 1) return v.toFixed(3);
  return v.toFixed(4);
}

export default async function MetricInsightPage({
  params,
}: {
  params: Promise<{ fqn: string }>;
}) {
  const { fqn } = await params;
  const decodedFqn = decodeURIComponent(fqn);
  const [metric, profile] = await Promise.all([
    serverFetch<MetricDetail>(`/metrics/${encodeURIComponent(decodedFqn)}`, 30),
    serverFetch<MetricProfile>(`/metrics/${encodeURIComponent(decodedFqn)}/profile`, 30),
  ]);
  if (!metric) notFound();

  const verdictColor =
    metric.current_verdict === "fail" ? "var(--fail)" :
    metric.current_verdict === "warn" ? "var(--warn)" :
    metric.current_verdict === "pass" ? "var(--pass)" : "var(--fg-3)";

  const stats: { label: string; value: string; dim?: boolean }[] = profile ? [
    { label: "Current", value: metric.current_value != null ? fmt(metric.current_value) : "—", dim: metric.current_value == null },
    { label: "p25", value: fmt(profile.p25) },
    { label: "Median", value: fmt(profile.median) },
    { label: "p75", value: fmt(profile.p75) },
    { label: "13w Mean", value: fmt(profile.trailing_13w_mean) },
    { label: "CV", value: (profile.cv * 100).toFixed(1) + "%" },
    { label: "Min", value: fmt(profile.min) },
    { label: "Max", value: fmt(profile.max) },
  ] : [];

  return (
    <div className="p-6 max-w-5xl">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 mb-4">
        <Link href="/metrics" className="t-small hover:opacity-80"
              style={{ color: "var(--accent)", fontFamily: "var(--font-jetbrains-mono)" }}>
          Metrics
        </Link>
        <span style={{ color: "var(--fg-3)", fontSize: 12 }}>/</span>
        <span className="t-small font-mono" style={{ color: "var(--fg-2)" }}>{metric.display_name}</span>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between mb-1">
        <div>
          <div className="flex items-center gap-3 mb-0.5">
            <h1 className="t-h1" style={{ color: "var(--fg-0)" }}>{metric.display_name}</h1>
            {metric.current_verdict && (
              <span className="t-micro px-1.5 py-0.5 font-mono"
                    style={{ background: verdictColor + "18", color: verdictColor,
                             fontFamily: "var(--font-jetbrains-mono)" }}>
                {metric.current_verdict}
              </span>
            )}
          </div>
          <p className="t-micro font-mono mb-2" style={{ color: "var(--fg-3)" }}>{metric.fqn}</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {metric.owners.map((o) => (
            <span key={o} className="t-micro px-2 py-0.5 border border-line"
                  style={{ color: "var(--fg-2)" }}>{o}</span>
          ))}
          <SubscribeButton metricFqn={decodedFqn} />
        </div>
      </div>

      {/* Profile panel: definition, grain, additivity, direction, cadence, lineage — editable */}
      <MetricProfilePanel
        fqn={decodedFqn}
        description={metric.description}
        grain={metric.grain}
        additivity={metric.additivity}
        good_direction={metric.good_direction}
        refresh_cadence={metric.refresh_cadence}
        lineage={metric.lineage}
        source_id={metric.source_id}
        expr_type={metric.expr_type}
        expr_sql={metric.expr_sql}
        numerator_sql={metric.numerator_sql}
        denominator_sql={metric.denominator_sql}
        filter_sql={metric.filter_sql}
      />

      {/* Meta line */}
      <div className="flex items-center gap-4 mb-5 t-micro"
           style={{ color: "var(--fg-3)", borderTop: "1px solid var(--line)", paddingTop: "10px" }}>
        <span>dataset: <span className="font-mono">{metric.dataset}</span></span>
        <span>kind: <span className="font-mono">{metric.kind}</span></span>
        {metric.last_run && <span>last run: {metric.last_run}</span>}
        {metric.tags.map((t) => (
          <span key={t} className="font-mono" style={{ color: "var(--accent)" }}>#{t}</span>
        ))}
      </div>

      {/* Stats strip — 8 cells */}
      {profile && stats.length > 0 && (
        <div className="grid grid-cols-8 gap-px mb-5" style={{ background: "var(--line)" }}>
          {stats.map(({ label, value, dim }) => (
            <div key={label} className="px-3 py-2.5" style={{ background: "var(--bg-1)" }}>
              <p className="t-micro mb-0.5" style={{ color: "var(--fg-3)" }}>{label}</p>
              <p className="t-small font-mono" style={{ color: dim ? "var(--fg-3)" : "var(--fg-0)" }}>{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Seasonality + Known issues */}
      {profile && (profile.seasonality.length > 0 || profile.known_data_issues.length > 0) && (
        <div className="grid grid-cols-[1fr_1fr] gap-4 mb-6">
          {profile.seasonality.length > 0 && (
            <div className="border border-line p-3" style={{ background: "var(--bg-1)" }}>
              <SeasonalityChart data={profile.seasonality} mean={profile.mean} />
            </div>
          )}
          {(
            <div className="border border-line p-3" style={{ background: "var(--bg-1)" }}>
              <p className="t-micro mb-2" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                Known data issues
              </p>
              {profile.known_data_issues.length === 0 ? (
                <p className="t-small" style={{ color: "var(--pass)" }}>No recent issues</p>
              ) : (
                <div className="space-y-1.5">
                  {profile.known_data_issues.map((issue, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span
                        className="t-micro px-1.5 py-0.5 flex-shrink-0 font-mono"
                        style={{
                          background: issue.verdict === "fail" ? "var(--fail-bg)" : "rgba(217,181,102,0.1)",
                          color: issue.verdict === "fail" ? "var(--fail)" : "var(--warn)",
                        }}
                      >
                        {issue.verdict}
                      </span>
                      <div className="min-w-0">
                        <p className="t-micro" style={{ color: "var(--fg-1)" }}>{issue.message}</p>
                        {issue.column && (
                          <p className="t-micro font-mono" style={{ color: "var(--fg-3)" }}>{issue.column}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Client component handles streaming narrative, reconciliation, evidence, chart */}
      <Suspense>
        <InsightClient
          fqn={decodedFqn}
          metric={metric}
          histogram={profile?.histogram ?? []}
          warnThreshold={metric.warn_threshold}
          failThreshold={metric.fail_threshold}
        />
      </Suspense>
    </div>
  );
}
