"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getToken } from "@/lib/auth";

const GITHUB_URL = "https://github.com/antonbarr-data/dqt";

const LOGO_TOOLTIP = "質 (shitsu) — quality, substance, the inner nature of a thing. The kanji points to what something truly is, not how it appears. dqt is meant to work the same way: concerned with the truth of the data, not its surface. The mark is also a quiet acknowledgment of a tradition I have learned much from — one in which quality and craft are understood to be the same thing. — Anton Barr";

function LogoMark({ size = "nav" }: { size?: "nav" | "footer" }) {
  const [visible, setVisible] = useState(false);
  const monoSize = size === "nav" ? 26 : 20;
  const kanjiSize = size === "nav" ? 22 : 20;
  return (
    <div className="relative" style={{ display: "inline-flex" }}
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      <Link href="/" className="flex items-center gap-2" style={{ textDecoration: "none" }}>
        <span style={{ fontSize: kanjiSize, lineHeight: 1, color: "var(--accent)" }}>質</span>
        <span style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: monoSize, fontWeight: 500, letterSpacing: "-0.05em", color: "var(--accent)" }}>dqt</span>
      </Link>
      {visible && (
        <div
          style={{
            position: "absolute",
            top: size === "footer" ? "auto" : "calc(100% + 10px)",
            bottom: size === "footer" ? "calc(100% + 10px)" : "auto",
            left: 0,
            width: 320,
            background: "var(--bg-2)",
            border: "1px solid var(--line)",
            padding: "14px 16px",
            zIndex: 50,
            pointerEvents: "none",
          }}
        >
          <p style={{ fontSize: 12, color: "var(--fg-1)", lineHeight: 1.75, margin: 0 }}>
            {LOGO_TOOLTIP}
          </p>
        </div>
      )}
    </div>
  );
}

const DETECTORS = [
  // univariate outliers
  "mad_outlier_fraction", "double_mad_outlier_fraction", "zscore_outlier_fraction",
  "adjusted_boxplot_fraction", "auto_outlier_fraction", "isolation_forest_fraction",
  "grubbs", "generalized_esd", "iqr_fence",
  // distribution & drift
  "ks_pvalue", "wasserstein_1", "psi", "kl_divergence", "js_divergence",
  "mmd", "adwin", "chi_square_drift",
  // time series
  "stl_residual_zscore", "bocpd", "cusum", "page_hinkley",
  "matrix_profile", "holt_winters", "prophet_anomaly",
  // multivariate
  "mahalanobis_distance", "lof", "one_class_svm", "hbos", "ecod",
  // associations & information
  "cramers_v", "mutual_information",
  // pattern
  "benford_law_fit",
];

const SIMPLE_CHECKS = [
  // nullness & completeness
  "null_fraction", "completeness", "date_part_missing_fraction",
  // uniqueness & volume
  "uniqueness", "composite_uniqueness", "volume",
  // numeric range
  "numeric_mean", "value_in_range", "max_in_range", "min_in_range",
  "median_in_range", "sum_in_range", "stddev_in_range",
  "cardinality_in_range", "quantile_in_range", "row_count_in_range",
  // categorical
  "set_membership", "set_exclusion",
  // string & format
  "regex_match", "string_length_range", "string_case_violation", "date_format",
  // relational
  "column_pair_comparison", "referential_integrity_rate",
  // structural & freshness
  "monotonicity", "freshness_seconds_behind", "schema_change",
  // custom SQL
  "sql_assertion_violation",
];

const CAPABILITIES = [
  {
    label: "Statistical detectors",
    slugline: "Every column. Every run.",
    desc: "MAD, double-MAD, isolation forest, KS, STL residual z-scores, adjusted boxplot fences. Plus completeness, validity, freshness, schema-change, and SQL-assertion checks. Every detector returns the same (verdict, score, plain_english) shape.",
    mono: "mad_outlier_fraction · ks_pvalue · stl_residual_zscore · isolation_forest_fraction",
    borderColor: "var(--accent)",
    labelColor: "var(--accent)",
  },
  {
    label: "Column-level lineage",
    slugline: "Parsed from your SQL.",
    desc: "dqt walks your dbt manifest and warehouse DDL with sqlglot to build a column-level dependency graph. From any incident, get an automatic blast radius — every downstream table and metric, ranked by exposure.",
    mono: null,
    borderColor: "var(--warn)",
    labelColor: "var(--warn)",
  },
  {
    label: "LLM Wiki · Semantic layer",
    slugline: "raw/ holds facts. wiki/ holds knowledge.",
    desc: "dqt uses Karpathy's LLM Wiki pattern. Dump your Trello tickets, SQL files, and BI reports into raw/. Point Claude Code at the vault. It synthesises wiki/ — dataset descriptions, metric definitions, causal edges — from the artifacts your team already has. YAML contracts compatible with dbt's semantic_models.yml.",
    mono: "raw/tickets/ · raw/sql/ · raw/reports/ → wiki/metrics/ · wiki/lineage/",
    borderColor: "var(--fg-3)",
    labelColor: "var(--fg-2)",
  },
  {
    label: "Causal discovery",
    slugline: "Granger. PCMCI+. Transfer Entropy.",
    desc: "dqt runs causal discovery across your metric time series, prunes edges with stability selection, and proposes directed metric→metric relationships annotated with lag, confidence, and E-values. Every edge reviewed by a human before entering the production DAG.",
    mono: null,
    borderColor: "var(--pass)",
    labelColor: "var(--pass)",
    highlight: true,
  },
];

const COMPARISON = [
  { label: "Open source (MIT)", dqt: true, gx: true, soda: "partial", elementary: true, dataplex: false },
  { label: "30+ statistical detectors", dqt: true, gx: "~", soda: "limited", elementary: "~", dataplex: true },
  { label: "Column-level lineage", dqt: true, gx: false, soda: false, elementary: "partial", dataplex: true },
  { label: "Causal discovery", dqt: true, gx: false, soda: false, elementary: false, dataplex: false },
  { label: "AI-grounded incident explainer", dqt: true, gx: false, soda: false, elementary: "partial", dataplex: true },
  { label: "pip install, runs offline", dqt: true, gx: true, soda: "partial", elementary: "partial", dataplex: false },
  { label: "No vendor lock-in", dqt: true, gx: true, soda: "partial", elementary: "partial", dataplex: false },
];

const INTEGRATIONS = [
  { name: "dbt", note: "reads manifest.json and semantic_models.yml directly" },
  { name: "Airflow · Dagster · Prefect", note: "runs as one Python task" },
  { name: "Snowflake · BigQuery · Postgres · Databricks", note: "adapter-based; bring your own connection" },
  { name: "OpenLineage", note: "ingests events from any non-dbt pipeline" },
  { name: "DuckDB", note: "embedded analytics engine for sample-level stats" },
];

const PYTHON_SNIPPET = `from dqt import Check, Runner, MemoryStore

check = Check(
    schema_name="public",
    table_name="orders",
    column_name="amount",
    detector_slug="mad_outlier_fraction",
)

result = Runner(MemoryStore()).run(check, adapter)

print(result.plain_english)
# → "0.82% of values are outliers — within the 1% warn threshold"`;

function CellValue({ v }: { v: boolean | string }) {
  if (v === true) return <span style={{ color: "var(--pass)", fontWeight: 600 }}>✓</span>;
  if (v === false) return <span style={{ color: "var(--fg-3)" }}>—</span>;
  if (v === "partial") return <span style={{ color: "var(--warn)" }}>partial</span>;
  return <span style={{ color: "var(--fg-2)" }}>{v}</span>;
}

type TabKey = "python" | "yaml" | "cli";

export default function RootPage() {
  const router = useRouter();
  const [tab, setTab] = useState<TabKey>("python");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (getToken()) router.replace("/overview");
  }, [router]);

  function copyInstall() {
    navigator.clipboard.writeText("pip install dqtlib").then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  const tabContent: Record<TabKey, string> = {
    python: PYTHON_SNIPPET,
    yaml: `checks:
  - schema_name: public
    table_name: orders
    column_name: amount
    detector_slug: mad_outlier_fraction
    scope:
      mode: incremental
      key_col: created_at
      since: "2024-01-01"
    sampling_pct: 25.0`,
    cli: `$ dqt run --config checks.yaml

✓  public.orders.amount  mad_outlier_fraction  pass  0.82%
⚠  public.sessions.duration  ks_pvalue  warn  p=0.031
✗  public.events.user_id  null_fraction  fail  12.4%`,
  };

  return (
    <div style={{ background: "var(--bg-0)", minHeight: "100vh", color: "var(--fg-0)" }}>

      {/* ── nav ── */}
      <nav
        className="flex items-center justify-between px-8 border-b border-line sticky top-0 z-10"
        style={{ height: 52, background: "var(--bg-1)" }}
      >
        <LogoMark size="nav" />
        <div className="flex items-center gap-8">
          <a href="#why" className="t-small transition-opacity hover:opacity-70" style={{ color: "var(--fg-1)" }}>Why dqt</a>
          <a href="#code" className="t-small transition-opacity hover:opacity-70" style={{ color: "var(--fg-1)" }}>Code</a>
          <a href="#compare" className="t-small transition-opacity hover:opacity-70" style={{ color: "var(--fg-1)" }}>vs. alternatives</a>
        </div>
        <div className="flex items-center gap-2">
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="t-small border border-line px-3 py-1.5 transition-colors hover:bg-bg-2"
            style={{ color: "var(--fg-0)" }}
          >
            GitHub ↗
          </a>
          <Link
            href="/login"
            className="t-small border px-3 py-1.5 transition-colors hover:opacity-80"
            style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)", fontWeight: 600 }}
          >
            Sign in
          </Link>
        </div>
      </nav>

      {/* ── hero ── */}
      <section className="px-8 pt-12 pb-10 max-w-5xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <span
            className="px-2.5 py-1 border t-small"
            style={{ color: "var(--fg-0)", borderColor: "var(--line-2)", background: "var(--bg-2)", fontFamily: "var(--font-jetbrains-mono)", fontSize: 11 }}
          >
            Open source · MIT licensed
          </span>
          <button
            onClick={copyInstall}
            className="px-2.5 py-1 border flex items-center gap-2 transition-colors hover:opacity-80"
            style={{
              color: "var(--fg-0)",
              borderColor: "var(--accent)",
              background: "rgba(157,208,176,0.08)",
              fontFamily: "var(--font-jetbrains-mono)",
              fontSize: 11,
            }}
          >
            <span style={{ color: "var(--accent)" }}>$</span>
            pip install dqtlib
            <span style={{ color: "var(--accent)", marginLeft: 4 }}>{copied ? "✓" : "⎘"}</span>
          </button>
          <a
            href="https://claude.com/plugins/context7"
            target="_blank"
            rel="noopener noreferrer"
            className="px-2.5 py-1 border flex items-center gap-1.5 transition-colors hover:opacity-80"
            style={{
              color: "var(--fg-1)",
              borderColor: "var(--line-2)",
              background: "var(--bg-2)",
              fontSize: 11,
            }}
          >
            <span style={{ color: "var(--accent)", fontSize: 10 }}>◆</span>
            Context7 plugin
          </a>
        </div>

        <h1 style={{ fontSize: "clamp(48px, 6.5vw, 84px)", fontWeight: 200, letterSpacing: "-0.03em", lineHeight: 1.04, color: "var(--fg-0)", maxWidth: 740 }}>
          Data quality that tells you <em style={{ fontStyle: "normal", color: "var(--accent)" }}>why</em>.
        </h1>

        <p className="mt-5" style={{ fontSize: 16, color: "var(--fg-1)", maxWidth: 540, lineHeight: 1.7 }}>
          Statistical drift detection, column-level lineage, and causal discovery — for dbt, warehouses, and data lakes. In one Python library.
        </p>

        <p className="mt-3 flex items-center gap-2 flex-wrap" style={{ fontSize: 12, color: "var(--fg-2)" }}>
          <span>Built for</span>
          <span className="px-2 py-0.5 border" style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 11, color: "var(--fg-0)", borderColor: "var(--line-2)", background: "var(--bg-2)" }}>ClickHouse</span>
          <span>and</span>
          <span className="px-2 py-0.5 border" style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 11, color: "var(--fg-0)", borderColor: "var(--line-2)", background: "var(--bg-2)" }}>BigQuery</span>
          <span>first.</span>
          <span style={{ color: "var(--line-2)" }}>·</span>
          <span className="px-2 py-0.5 border" style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 11, color: "var(--warn)", borderColor: "var(--warn)", background: "rgba(217,181,102,0.07)" }}>Postgres · Snowflake · others — WIP</span>
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: "var(--accent)", fontSize: 12, borderBottom: "1px solid rgba(157,208,176,0.4)", textDecoration: "none" }}
          >
            contributors welcome ↗
          </a>
        </p>

        <div className="mt-6 border-l-2 pl-4 py-1" style={{ borderColor: "var(--accent)", maxWidth: 560 }}>
          <p style={{ fontSize: 11, color: "var(--accent)", letterSpacing: "0.12em", textTransform: "uppercase", fontWeight: 500, marginBottom: 6 }}>
            New · LLM Wiki semantic layer
          </p>
          <p style={{ fontSize: 15, color: "var(--fg-0)", fontWeight: 400, lineHeight: 1.55, marginBottom: 8 }}>
            Your Trello board is already a semantic layer. dqt extracts it.
          </p>
          <p style={{ fontSize: 13, color: "var(--fg-1)", lineHeight: 1.7, marginBottom: 10 }}>
            Dump tickets, SQL, and BI reports into{" "}
            <span style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 12, color: "var(--fg-0)" }}>raw/</span>.
            Point Claude Code at the vault — it synthesises dataset descriptions, metric definitions, and causal edges into{" "}
            <span style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 12, color: "var(--fg-0)" }}>wiki/</span>.
            No manual YAML authoring.
          </p>
          <a
            href="https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f"
            target="_blank"
            rel="noopener noreferrer"
            style={{ fontSize: 12, color: "var(--fg-1)", textDecoration: "none" }}
            className="transition-opacity hover:opacity-70"
          >
            Based on Karpathy&apos;s LLM Wiki pattern ↗
          </a>
        </div>

        <div className="flex items-center gap-3 mt-8 flex-wrap">
          <button
            onClick={copyInstall}
            className="flex items-center gap-2 px-5 py-3 border transition-colors hover:opacity-85"
            style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)", fontWeight: 600 }}
          >
            <span style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 13 }}>pip install dqtlib</span>
            <span style={{ fontSize: 14 }}>{copied ? "✓" : "⎘"}</span>
          </button>
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-5 py-3 border border-line transition-colors hover:bg-bg-2"
            style={{ color: "var(--fg-0)", fontSize: 13 }}
          >
            ★ Star on GitHub →
          </a>
        </div>
      </section>

      {/* ── stats band ── */}
      <section className="border-t border-b border-line" style={{ background: "var(--bg-1)" }}>
        <div className="grid mx-auto" style={{ maxWidth: 900, gridTemplateColumns: "repeat(4, 1fr)" }}>
          {[
            { value: "30+", label: "detector algorithms", color: "var(--accent)" },
            { value: "9+", label: "warehouse engines", color: "var(--accent)" },
            { value: "100B+", label: "rows validated (and counting)", color: "var(--warn)" },
            { value: "MIT", label: "no vendor lock-in", color: "var(--pass)" },
          ].map((s, i) => (
            <div key={s.label} className="px-8 py-5 text-center" style={{ borderRight: i < 3 ? "1px solid var(--line)" : "none" }}>
              <p style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 36, fontWeight: 300, color: s.color, letterSpacing: "-0.03em" }}>
                {s.value}
              </p>
              <p style={{ fontSize: 10, color: "var(--fg-2)", letterSpacing: "0.1em", textTransform: "uppercase", marginTop: 4 }}>{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── problem agitation ── */}
      <section id="why" className="px-8 py-14 max-w-5xl mx-auto">
        <p style={{ fontSize: 10, color: "var(--fg-1)", letterSpacing: "0.14em", textTransform: "uppercase", marginBottom: 10 }}>The hour after the alert</p>
        <h2 style={{ fontSize: "clamp(28px, 3.5vw, 44px)", fontWeight: 300, letterSpacing: "-0.02em", lineHeight: 1.15, marginBottom: 24 }}>
          Most DQ tools tell you a row count dropped.<br />They don&apos;t tell you why.
        </h2>
        <div className="grid grid-cols-2 gap-10">
          <div className="space-y-4">
            <p style={{ fontSize: 14, color: "var(--fg-1)", lineHeight: 1.75 }}>
              You set a threshold. It fires. Slack lights up. Now you&apos;re bouncing between dbt docs, the warehouse, and your BI tool — trying to figure out which upstream model changed, whether the spike in nulls explains the dashboard regression, and whether this is worth waking the on-call engineer for.
            </p>
            <p style={{ fontSize: 14, color: "var(--fg-0)", lineHeight: 1.75 }}>
              <strong>dqt was built for the part that comes after the alert.</strong> It reads your dbt manifest, parses your warehouse SQL into a column-level lineage graph, runs 30+ statistical detectors, and discovers causal relationships across your metrics — so the next time something moves, you already know what moved it.
            </p>
          </div>
          <div className="space-y-3">
            <div className="p-4 border border-line" style={{ background: "var(--bg-1)" }}>
              <p style={{ fontSize: 10, color: "var(--fail)", letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 8, fontWeight: 500 }}>Without dqt</p>
              <div className="space-y-2">
                <div className="flex items-start gap-2">
                  <span style={{ color: "var(--fail)" }}>✗</span>
                  <span style={{ fontSize: 13, color: "var(--fg-1)" }}>orders.amount null_fraction ≥ 0.05 — threshold exceeded</span>
                </div>
                <p style={{ fontSize: 11, color: "var(--fg-3)", paddingLeft: 20 }}>Now what? Go dig through git log, dbt docs, warehouse history…</p>
              </div>
            </div>
            <div className="p-4 border" style={{ background: "var(--bg-1)", borderColor: "var(--accent)" }}>
              <p style={{ fontSize: 10, color: "var(--accent)", letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 8, fontWeight: 500 }}>With dqt</p>
              <div className="space-y-2">
                <div className="flex items-start gap-2">
                  <span style={{ color: "var(--fail)" }}>✗</span>
                  <span style={{ fontSize: 13, color: "var(--fg-0)" }}>orders.amount null_fraction = 12.4% (baseline 0.3%)</span>
                </div>
                <p style={{ fontSize: 13, color: "var(--fg-1)", paddingLeft: 20, lineHeight: 1.6 }}>
                  Causal trace: <span style={{ color: "var(--accent)", fontFamily: "var(--font-jetbrains-mono)", fontSize: 12 }}>stg_payments → orders → revenue</span>. Upstream model <span style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 12 }}>stg_payments</span> introduced a schema break 6h ago. E-value = 3.2.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── capabilities ── */}
      <section className="border-t border-line px-8 py-14" style={{ background: "var(--bg-1)" }}>
        <div className="max-w-5xl mx-auto">
          <p style={{ fontSize: 10, color: "var(--fg-1)", letterSpacing: "0.14em", textTransform: "uppercase", marginBottom: 24 }}>Four layers. One library.</p>
          <div className="grid grid-cols-2 gap-px" style={{ background: "var(--line)" }}>
            {CAPABILITIES.map((c) => (
              <div key={c.label} className="p-6 space-y-2" style={{ background: "var(--bg-1)", borderLeft: `2px solid ${c.borderColor}` }}>
                <p style={{ fontSize: 10, color: c.labelColor, letterSpacing: "0.12em", textTransform: "uppercase", fontWeight: 500 }}>{c.label}</p>
                <h3 style={{ fontSize: 18, fontWeight: 400, color: "var(--fg-0)", letterSpacing: "-0.01em" }}>{c.slugline}</h3>
                <p style={{ fontSize: 13, color: "var(--fg-1)", lineHeight: 1.7 }}>{c.desc}</p>
                {c.mono && (
                  <p style={{ fontSize: 11, color: "var(--fg-2)", fontFamily: "var(--font-jetbrains-mono)", lineHeight: 1.8, paddingTop: 4 }}>{c.mono}</p>
                )}
                {c.highlight && (
                  <p style={{ fontSize: 11, color: "var(--pass)", paddingTop: 4, fontWeight: 500 }}>The only DQ tool that ships causal discovery.</p>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── LLM Wiki ── */}
      <section className="border-t border-line px-8 py-14 max-w-5xl mx-auto">
        <div className="grid grid-cols-2 gap-12 items-start">
          <div>
            <p style={{ fontSize: 10, color: "var(--fg-1)", letterSpacing: "0.14em", textTransform: "uppercase", marginBottom: 10 }}>
              <a href="https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f" target="_blank" rel="noopener noreferrer" style={{ color: "var(--fg-1)", borderBottom: "1px solid var(--line)" }}>Karpathy&apos;s LLM Wiki pattern</a>
            </p>
            <h2 style={{ fontSize: "clamp(24px, 3vw, 40px)", fontWeight: 300, letterSpacing: "-0.02em", lineHeight: 1.2, marginBottom: 16 }}>
              Your data warehouse<br />already has documentation.<br />It&apos;s in your Trello board.
            </h2>
            <p style={{ fontSize: 14, color: "var(--fg-1)", lineHeight: 1.75, marginBottom: 12 }}>
              Every BI request your GTM team filed is a semantic definition waiting to be extracted. The ticket says what the metric means. The SQL says how it&apos;s computed. The report says what thresholds matter.
            </p>
            <p style={{ fontSize: 14, color: "var(--fg-1)", lineHeight: 1.75, marginBottom: 20 }}>
              dqt uses Karpathy&apos;s LLM Wiki structure: <span style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 12, color: "var(--fg-0)" }}>raw/</span> for atomic source documents, <span style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 12, color: "var(--fg-0)" }}>wiki/</span> for synthesised knowledge. Point Claude Code at the vault and it writes the semantic layer for you — from the artifacts your team already has.
            </p>
            <a
              href={GITHUB_URL + "/blob/main/docs/semantic-layer.md"}
              target="_blank"
              rel="noopener noreferrer"
              style={{ fontSize: 13, color: "var(--accent)", borderBottom: "1px solid var(--accent)" }}
            >
              Read the full workflow guide →
            </a>
          </div>
          <div className="space-y-0 border border-line" style={{ background: "var(--bg-1)" }}>
            {[
              { step: "1", label: "Export Trello tickets + attachments", sub: "SQL files, report HTMLs, metric definitions", color: "var(--fg-3)" },
              { step: "2", label: "Put them in raw/", sub: "raw/tickets/ · raw/sql/ · raw/reports/ · raw/schema/", color: "var(--fg-3)" },
              { step: "3", label: "Point Claude Code at the vault", sub: "cd vault && claude .", color: "var(--accent)" },
              { step: "4", label: "Claude Code synthesises wiki/", sub: "datasets, metrics, lineage, causal edges — grounded in your actual data", color: "var(--accent)" },
              { step: "5", label: "dqt generates per-column docs + checks", sub: "write_vault() · dqt run checks.yaml", color: "var(--pass)" },
            ].map((s, i) => (
              <div key={i} className="flex items-start gap-4 px-5 py-4 border-b border-line last:border-0">
                <span style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 11, color: s.color, minWidth: 16, paddingTop: 1 }}>{s.step}</span>
                <div>
                  <p style={{ fontSize: 13, color: "var(--fg-0)", fontWeight: 500 }}>{s.label}</p>
                  <p style={{ fontSize: 11, color: "var(--fg-2)", fontFamily: "var(--font-jetbrains-mono)", marginTop: 2 }}>{s.sub}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Claude Code + plugins ── */}
      <section className="border-t border-line px-8 py-14" style={{ background: "var(--bg-1)" }}>
        <div className="max-w-5xl mx-auto">
          <p style={{ fontSize: 10, color: "var(--accent)", letterSpacing: "0.14em", textTransform: "uppercase", marginBottom: 10, fontWeight: 500 }}>
            Recommended workflow
          </p>
          <h2 style={{ fontSize: "clamp(24px, 3vw, 40px)", fontWeight: 300, letterSpacing: "-0.02em", lineHeight: 1.2, marginBottom: 6 }}>
            Use dqt with Claude Code.
          </h2>
          <p style={{ fontSize: 14, color: "var(--fg-1)", lineHeight: 1.75, marginBottom: 32, maxWidth: 600 }}>
            Three plugins turn Claude Code into a grounded data-quality engineer that knows your warehouse, knows the dqt API, and can run checks from natural language.
          </p>

          <div className="grid grid-cols-3 gap-0 border border-line">
            {[
              {
                num: "1",
                badge: "Context7",
                href: "https://claude.com/plugins/context7",
                title: "Up-to-date dqt docs",
                desc: "Connects Claude Code to dqt's live documentation and source — all 38 detector slugs, the exact YAML schema, and adapter protocol. No training-data lag.",
                bullets: [
                  "Write checks from business rules",
                  "Pick the right detector for your data shape",
                  "Debug failures with current API knowledge",
                ],
                color: "var(--accent)",
              },
              {
                num: "2",
                badge: "Superpowers",
                href: "https://claude.com/plugins/superpowers",
                title: "Agentic development skills",
                desc: "Gives Claude Code structured workflows for planning, executing, and reviewing multi-step tasks — essential for building out a full dqt check suite or semantic layer from scratch.",
                bullets: [
                  "Plan + execute check suites step by step",
                  "TDD for detector configs",
                  "Subagent-driven semantic layer build",
                ],
                color: "var(--warn)",
              },
              {
                num: "3",
                badge: "Warehouse MCP",
                href: "https://github.com/ClickHouse/mcp-clickhouse",
                title: "Live warehouse access",
                desc: "Each warehouse publishes its own MCP — e.g. mcp-clickhouse for ClickHouse, or the Postgres MCP server. Connect Claude Code to your warehouse and it can inspect live schemas, sample real distributions, and write dqt checks grounded in your actual data.",
                bullets: [
                  "Schema introspection from live tables",
                  "Sample-driven detector recommendations",
                  "Auto-generate semantic.yaml from DDL",
                ],
                color: "var(--pass)",
              },
            ].map((plugin, i) => (
              <div key={i} className="px-6 py-6 border-r border-line last:border-0">
                <div className="flex items-center gap-2 mb-4">
                  <span style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 10, color: "var(--fg-3)" }}>{plugin.num}</span>
                  <a
                    href={plugin.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-2 py-0.5 border transition-colors hover:opacity-80"
                    style={{ color: plugin.color, borderColor: plugin.color, fontSize: 11, fontWeight: 600 }}
                  >
                    {plugin.badge} ↗
                  </a>
                </div>
                <h3 style={{ fontSize: 16, fontWeight: 400, color: "var(--fg-0)", letterSpacing: "-0.01em", marginBottom: 8 }}>{plugin.title}</h3>
                <p style={{ fontSize: 13, color: "var(--fg-1)", lineHeight: 1.7, marginBottom: 14 }}>{plugin.desc}</p>
                <ul className="space-y-1.5">
                  {plugin.bullets.map((b, j) => (
                    <li key={j} className="flex items-start gap-2">
                      <span style={{ color: plugin.color, fontSize: 10, paddingTop: 3 }}>▸</span>
                      <span style={{ fontSize: 13, color: "var(--fg-1)" }}>{b}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <div className="mt-6 border border-line" style={{ background: "var(--bg-0)" }}>
            <div className="px-4 py-2 border-b border-line flex items-center gap-2" style={{ background: "var(--bg-2)" }}>
              <span style={{ fontSize: 10, color: "var(--fg-1)", letterSpacing: "0.1em", textTransform: "uppercase" }}>Claude Code · all three plugins active</span>
            </div>
            <div className="grid grid-cols-2 divide-x divide-line">
              {[
                { role: "user", text: "Look at my orders table and write dqt checks for amount_usd. Flag outliers and distribution shift." },
                { role: "assistant", text: "Querying your warehouse via MCP... orders.amount_usd: right-skewed, p99=$4,820.\n\nContext7 confirms: use adjusted_boxplot_fraction (handles skew via medcouple) + ks_pvalue for drift.\n\nchecks:\n  - table_name: orders\n    column_name: amount_usd\n    detector_slug: adjusted_boxplot_fraction\n  - table_name: orders\n    column_name: amount_usd\n    detector_slug: ks_pvalue\n    params: {alpha: 0.01}" },
              ].map((msg, i) => (
                <div key={i} className="px-4 py-3">
                  <p style={{ fontSize: 10, color: msg.role === "user" ? "var(--fg-2)" : "var(--accent)", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 4 }}>
                    {msg.role === "user" ? "you" : "claude code"}
                  </p>
                  <p style={{ fontSize: 11, color: "var(--fg-1)", lineHeight: 1.6, fontFamily: "var(--font-jetbrains-mono)", whiteSpace: "pre-wrap" }}>
                    {msg.text}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── detector catalog ── */}
      <section className="border-t border-line px-8 py-12 max-w-5xl mx-auto">
        <div className="space-y-8">
          <div>
            <p style={{ fontSize: 10, color: "var(--fg-1)", letterSpacing: "0.14em", textTransform: "uppercase", marginBottom: 12 }}>
              Statistical &amp; ML algorithms · {DETECTORS.length}
            </p>
            <div className="flex flex-wrap gap-x-3 gap-y-2">
              {DETECTORS.map((d) => (
                <span
                  key={d}
                  style={{
                    fontSize: 11,
                    color: "var(--fg-0)",
                    fontFamily: "var(--font-jetbrains-mono)",
                    background: "var(--bg-2)",
                    border: "1px solid var(--line)",
                    padding: "2px 8px",
                  }}
                >
                  {d}
                </span>
              ))}
            </div>
          </div>
          <div>
            <p style={{ fontSize: 10, color: "var(--fg-1)", letterSpacing: "0.14em", textTransform: "uppercase", marginBottom: 12 }}>
              Declarative checks · {SIMPLE_CHECKS.length}
            </p>
            <div className="flex flex-wrap gap-x-3 gap-y-2">
              {SIMPLE_CHECKS.map((d) => (
                <span
                  key={d}
                  style={{
                    fontSize: 11,
                    color: "var(--fg-1)",
                    fontFamily: "var(--font-jetbrains-mono)",
                    background: "var(--bg-1)",
                    border: "1px solid var(--line)",
                    padding: "2px 8px",
                  }}
                >
                  {d}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── code proof ── */}
      <section id="code" className="border-t border-line px-8 py-14" style={{ background: "var(--bg-1)" }}>
        <div className="max-w-5xl mx-auto">
          <p style={{ fontSize: 10, color: "var(--fg-1)", letterSpacing: "0.14em", textTransform: "uppercase", marginBottom: 10 }}>Three lines to your first check.</p>
          <h2 style={{ fontSize: "clamp(24px, 3vw, 40px)", fontWeight: 300, letterSpacing: "-0.02em", lineHeight: 1.2, marginBottom: 24 }}>
            Runs in notebooks. Runs in CI.<br />No server required.
          </h2>

          <div className="border border-line" style={{ background: "var(--bg-0)" }}>
            <div className="flex items-center border-b border-line" style={{ background: "var(--bg-2)" }}>
              {(["python", "yaml", "cli"] as TabKey[]).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className="px-4 py-2 transition-colors"
                  style={{
                    borderBottom: tab === t ? "2px solid var(--accent)" : "2px solid transparent",
                    color: tab === t ? "var(--fg-0)" : "var(--fg-2)",
                    fontFamily: "var(--font-jetbrains-mono)",
                    fontSize: 12,
                  }}
                >
                  {t}
                </button>
              ))}
            </div>
            <pre
              className="p-6 overflow-x-auto"
              style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 12, lineHeight: 1.75, color: "var(--fg-0)", margin: 0 }}
            >
              {tabContent[tab]}
            </pre>
          </div>

          <p style={{ fontSize: 13, color: "var(--fg-1)", lineHeight: 1.7, marginTop: 14 }}>
            No server required. The optional FastAPI service and dashboard are there when you want them — and stay out of the way when you don&apos;t.
          </p>
        </div>
      </section>

      {/* ── comparison table ── */}
      <section id="compare" className="border-t border-line px-8 py-14 max-w-5xl mx-auto">
        <p style={{ fontSize: 10, color: "var(--fg-1)", letterSpacing: "0.14em", textTransform: "uppercase", marginBottom: 10 }}>Where dqt sits.</p>
        <h2 style={{ fontSize: "clamp(24px, 3vw, 40px)", fontWeight: 300, letterSpacing: "-0.02em", lineHeight: 1.2, marginBottom: 8 }}>
          We borrowed the best ideas.<br />Then shipped the parts they don&apos;t have.
        </h2>
        <p style={{ fontSize: 13, color: "var(--fg-1)", marginBottom: 24, lineHeight: 1.6 }}>
          Causal discovery isn&apos;t a nice-to-have — it&apos;s the difference between <em>&ldquo;orders are down&rdquo;</em> and <em>&ldquo;orders are down because the EU marketing-spend job missed its 06:00 run.&rdquo;</em>
        </p>

        <div className="border border-line overflow-x-auto" style={{ background: "var(--bg-1)" }}>
          <table className="w-full" style={{ borderCollapse: "collapse", minWidth: 640 }}>
            <thead>
              <tr style={{ background: "var(--bg-2)" }}>
                <th className="px-4 py-3 text-left" style={{ fontSize: 10, color: "var(--fg-2)", fontWeight: 400, letterSpacing: "0.1em", textTransform: "uppercase" }}>Capability</th>
                {[
                  { key: "dqt", label: "dqt", accent: true },
                  { key: "gx", label: "Great Expectations", accent: false },
                  { key: "soda", label: "Soda", accent: false },
                  { key: "elementary", label: "Elementary", accent: false },
                  { key: "dataplex", label: "Dataplex", accent: false },
                ].map((c) => (
                  <th key={c.key} className="px-4 py-3 text-center" style={{ fontSize: 11, color: c.accent ? "var(--accent)" : "var(--fg-2)", fontWeight: c.accent ? 700 : 400, letterSpacing: "0.06em" }}>
                    {c.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {COMPARISON.map((row, i) => (
                <tr key={row.label} className="border-t border-line" style={{ background: i % 2 === 0 ? "var(--bg-1)" : "var(--bg-0)" }}>
                  <td className="px-4 py-2.5" style={{ fontSize: 13, color: "var(--fg-0)" }}>{row.label}</td>
                  {[row.dqt, row.gx, row.soda, row.elementary, row.dataplex].map((v, j) => (
                    <td key={j} className="px-4 py-2.5 text-center" style={{ fontSize: 13 }}>
                      <CellValue v={v} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* ── integrations ── */}
      <section className="border-t border-line px-8 py-12" style={{ background: "var(--bg-1)" }}>
        <div className="max-w-5xl mx-auto">
          <p style={{ fontSize: 10, color: "var(--fg-1)", letterSpacing: "0.14em", textTransform: "uppercase", marginBottom: 16 }}>Drop it in next to the tools you already use.</p>
          <div className="border border-line" style={{ background: "var(--bg-0)" }}>
            {INTEGRATIONS.map((item, i) => (
              <div key={i} className="flex items-center gap-6 px-5 py-3 border-b border-line last:border-0">
                <span style={{ fontSize: 13, color: "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)", minWidth: 260 }}>{item.name}</span>
                <span style={{ fontSize: 13, color: "var(--fg-1)" }}>{item.note}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── final CTA ── */}
      <section className="border-t border-line px-8 py-20 text-center" style={{ background: "var(--bg-0)" }}>
        <h2 style={{ fontSize: "clamp(26px, 3.5vw, 48px)", fontWeight: 300, letterSpacing: "-0.02em", lineHeight: 1.2 }}>
          Install it. Point it at your warehouse.<br />See your first incident in five minutes.
        </h2>

        <button
          onClick={copyInstall}
          className="flex items-center gap-3 mx-auto mt-8 px-6 py-3 border transition-colors hover:opacity-85"
          style={{
            fontFamily: "var(--font-jetbrains-mono)",
            fontSize: 14,
            color: "var(--bg-0)",
            background: "var(--accent)",
            borderColor: "var(--accent)",
            fontWeight: 600,
          }}
        >
          <span>$</span>
          pip install dqtlib
          <span>{copied ? "✓ copied" : "⎘"}</span>
        </button>

        <div className="flex items-center justify-center gap-3 mt-4 flex-wrap">
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="px-5 py-2.5 border border-line transition-colors hover:bg-bg-2"
            style={{ fontSize: 13, color: "var(--fg-0)" }}
          >
            ★ Star on GitHub →
          </a>
          <Link
            href="/login"
            className="px-5 py-2.5 border transition-colors hover:opacity-80"
            style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)", fontWeight: 600, fontSize: 13 }}
          >
            Open the dashboard →
          </Link>
        </div>

        <p style={{ fontSize: 11, color: "var(--fg-2)", marginTop: 24, letterSpacing: "0.04em" }}>
          Open source · MIT licensed · Python 3.12+ · No telemetry · No signup · No credit card
        </p>
      </section>

      {/* ── footer ── */}
      <footer className="border-t border-line px-8 py-6" style={{ background: "var(--bg-1)" }}>
        <div className="flex items-start justify-between gap-12">
          <LogoMark size="footer" />
          <div className="flex items-center gap-6 pt-1">
            <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" style={{ fontSize: 12, color: "var(--fg-1)" }} className="transition-opacity hover:opacity-70">
              GitHub
            </a>
            <a href="https://www.linkedin.com/in/antonbar/" target="_blank" rel="noopener noreferrer" style={{ fontSize: 12, color: "var(--fg-1)" }} className="transition-opacity hover:opacity-70">
              LinkedIn
            </a>
            <span style={{ fontSize: 12, color: "var(--fg-2)" }}>MIT License</span>
            <span style={{ fontSize: 12, color: "var(--fg-2)" }}>Python 3.12+</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
