import { readFileSync } from "fs";
import { join } from "path";
import { QualityDashboard } from "./dashboard";

export const metadata = {
  title: "dqt / quality",
  description:
    "Per-detector precision, recall, and F1 benchmarks for the dqt library. Updated on each release.",
  icons: { icon: "/favicon.svg" },
};

export type DetectorRow = {
  slug: string;
  family: string;
  f1: number;
  precision: number | null;
  recall: number;
  fpr: number | null;
  n: number;
};

const FAMILY: Record<string, string> = {
  adwin: "drift",
  chi_square_drift: "drift",
  js_divergence: "drift",
  kl_divergence: "drift",
  ks_pvalue: "drift",
  mmd: "drift",
  outlier_fraction_drift: "drift",
  psi: "drift",
  wasserstein_1: "drift",
  bocpd: "timeseries",
  cusum: "timeseries",
  holt_winters: "timeseries",
  matrix_profile: "timeseries",
  monotonicity: "timeseries",
  page_hinkley: "timeseries",
  prophet_anomaly: "timeseries",
  stl_residual_zscore: "timeseries",
  adjusted_boxplot_fraction: "outlier",
  auto_outlier: "outlier",
  double_mad_outlier_fraction: "outlier",
  ecod: "outlier",
  generalized_esd: "outlier",
  grubbs: "outlier",
  hbos: "outlier",
  iqr_fence: "outlier",
  isolation_forest_fraction: "outlier",
  lof: "outlier",
  mad_outlier_fraction: "outlier",
  mahalanobis_distance: "outlier",
  one_class_svm: "outlier",
  zscore_outlier_fraction: "outlier",
  benford_law_fit: "distribution",
  cramers_v: "distribution",
  mutual_information: "distribution",
};

function slugFamily(slug: string): string {
  if (slug.startsWith("_")) return "baseline";
  return FAMILY[slug] ?? "rule";
}

function avg(vals: number[]): number {
  if (vals.length === 0) return 0;
  return vals.reduce((s, v) => s + v, 0) / vals.length;
}

function loadRows(): DetectorRow[] {
  try {
    const csvPath = join(process.cwd(), "public", "data", "results.csv");
    const text = readFileSync(csvPath, "utf-8");
    const lines = text.trim().split("\n");
    const headers = lines[0].split(",");
    const idx = (k: string) => headers.indexOf(k);

    const bySlug = new Map<string, { f1: number[]; p: number[]; r: number[] }>();
    for (const line of lines.slice(1)) {
      if (!line.trim()) continue;
      const cols = line.split(",");
      const slug = cols[idx("detector_slug")]?.trim();
      const f1 = parseFloat(cols[idx("f1")]);
      const pr = parseFloat(cols[idx("precision")]);
      const rc = parseFloat(cols[idx("recall")]);
      if (!slug || isNaN(f1)) continue;
      if (!bySlug.has(slug)) bySlug.set(slug, { f1: [], p: [], r: [] });
      const entry = bySlug.get(slug)!;
      entry.f1.push(f1);
      if (!isNaN(pr)) entry.p.push(pr);
      if (!isNaN(rc)) entry.r.push(rc);
    }

    const rows: DetectorRow[] = [];
    for (const [slug, vals] of Array.from(bySlug.entries())) {
      rows.push({
        slug,
        family: slugFamily(slug),
        f1: avg(vals.f1),
        precision: vals.p.length > 0 ? avg(vals.p) : null,
        recall: avg(vals.r),
        fpr: null,
        n: vals.f1.length,
      });
    }
    return rows.sort((a, b) => b.f1 - a.f1);
  } catch {
    return [];
  }
}

export default function QualityPage() {
  const rows = loadRows();
  return <QualityDashboard rows={rows} />;
}
