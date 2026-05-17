import { Suspense } from "react";
import { serverFetch } from "@/lib/server-api";
import { notFound } from "next/navigation";
import Link from "next/link";
import { InsightClient } from "./insight-client";
import { SubscribeButton } from "@/components/subscriptions/subscribe-button";

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
}

export default async function MetricInsightPage({
  params,
}: {
  params: Promise<{ fqn: string }>;
}) {
  const { fqn } = await params;
  const decodedFqn = decodeURIComponent(fqn);
  const metric = await serverFetch<MetricDetail>(`/metrics/${encodeURIComponent(decodedFqn)}`, 30);
  if (!metric) notFound();

  const verdictColor =
    metric.current_verdict === "fail" ? "var(--fail)" :
    metric.current_verdict === "warn" ? "var(--warn)" :
    metric.current_verdict === "pass" ? "var(--pass)" : "var(--fg-3)";

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
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="t-h1" style={{ color: "var(--fg-0)" }}>{metric.display_name}</h1>
            {metric.current_verdict && (
              <span className="t-micro px-1.5 py-0.5 font-mono"
                    style={{ background: verdictColor + "18", color: verdictColor,
                             fontFamily: "var(--font-jetbrains-mono)" }}>
                {metric.current_verdict}
              </span>
            )}
          </div>
          <p className="t-small font-mono mb-1" style={{ color: "var(--fg-3)" }}>{metric.fqn}</p>
          {metric.description && (
            <p className="t-small" style={{ color: "var(--fg-2)", maxWidth: 560 }}>{metric.description}</p>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {metric.owners.map((o) => (
            <span key={o} className="t-micro px-2 py-0.5 border border-line"
                  style={{ color: "var(--fg-2)" }}>{o}</span>
          ))}
          <SubscribeButton metricFqn={decodedFqn} />
        </div>
      </div>

      {/* Meta line */}
      <div className="flex items-center gap-4 mb-8 t-micro"
           style={{ color: "var(--fg-3)", borderBottom: "1px solid var(--line)", paddingBottom: "12px" }}>
        <span>dataset: <span className="font-mono">{metric.dataset}</span></span>
        <span>kind: <span className="font-mono">{metric.kind}</span></span>
        {metric.last_run && <span>last run: {metric.last_run}</span>}
        {metric.tags.map((t) => (
          <span key={t} className="font-mono" style={{ color: "var(--accent)" }}>#{t}</span>
        ))}
      </div>

      {/* Client component handles streaming narrative, reconciliation, evidence, chart */}
      <Suspense>
        <InsightClient fqn={decodedFqn} metric={metric} />
      </Suspense>
    </div>
  );
}
