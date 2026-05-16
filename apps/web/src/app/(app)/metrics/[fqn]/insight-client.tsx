"use client";

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

export function InsightClient({ fqn, metric }: { fqn: string; metric: MetricDetail }) {
  return null;
}
