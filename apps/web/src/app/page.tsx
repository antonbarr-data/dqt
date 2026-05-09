"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getToken } from "@/lib/auth";

const DETECTORS = [
  "mad_outlier_fraction", "ks_pvalue", "stl_residual_zscore",
  "isolation_forest_fraction", "wasserstein_1", "psi",
  "modified_zscore", "double_mad", "grubbs", "generalized_esd",
  "iqr_fence", "adjusted_boxplot", "bocpd", "cusum", "page_hinkley",
  "matrix_profile", "holt_winters", "prophet_anomaly",
  "kl_divergence", "js_divergence", "mmd", "adwin",
  "chi_square_drift", "cramers_v", "mutual_information",
  "mahalanobis_distance", "lof", "one_class_svm", "hbos", "ecod",
  "benford_law_fit", "null_fraction", "schema_change", "freshness_check",
];

const CAPABILITIES = [
  {
    label: "30+ statistical detectors",
    slugline: "Every column. Every run.",
    desc: "MAD, double-MAD, isolation forest, KS, STL residual z-scores, adjusted boxplot fences. Plus completeness, validity, freshness, schema-change, and SQL-assertion checks. Every detector returns the same (verdict, score, plain_english) shape — so they compose, swap, and stack.",
    mono: "mad_outlier_fraction · ks_pvalue · stl_residual_zscore · isolation_forest_fraction · referential_integrity_rate",
  },
  {
    label: "Column-level lineage",
    slugline: "Parsed from your SQL.",
    desc: "dqt walks your dbt manifest and warehouse DDL with sqlglot to build a column-level dependency graph. It also ingests OpenLineage events for non-dbt pipelines. From any incident, get an automatic blast radius — every downstream table and metric, ranked by exposure.",
    mono: null,
  },
  {
    label: "Semantic layer",
    slugline: "A knowledge vault, not a config file.",
    desc: "Define datasets, columns, and metrics as YAML contracts — compatible with dbt's semantic_models.yml out of the box. Every entity is a document, every relationship is a link, every description gets an embedding. Searchable by humans. Groundable by AI agents.",
    mono: null,
  },
  {
    label: "Causal discovery",
    slugline: "Granger. PCMCI+. Transfer Entropy.",
    desc: "dqt runs causal discovery across your metric time series, prunes edges with stability selection over bootstrap resamples, and proposes directed metric→metric relationships annotated with lag, confidence, and E-values. Every proposed edge is reviewed by a human owner before it enters the production DAG.",
    mono: null,
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
  if (v === true) return <span style={{ color: "var(--pass)" }}>✓</span>;
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
        <span style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 18, fontWeight: 300, letterSpacing: "-0.05em", color: "var(--accent)" }}>
          dqt
        </span>
        <div className="flex items-center gap-6">
          <a href="#why" className="t-small transition-opacity hover:opacity-70" style={{ color: "var(--fg-2)" }}>Why dqt</a>
          <a href="#code" className="t-small transition-opacity hover:opacity-70" style={{ color: "var(--fg-2)" }}>Code</a>
          <a href="#compare" className="t-small transition-opacity hover:opacity-70" style={{ color: "var(--fg-2)" }}>vs. alternatives</a>
        </div>
        <div className="flex items-center gap-2">
          <a
            href="https://github.com/anthropics/dqt"
            target="_blank"
            rel="noopener noreferrer"
            className="t-small border border-line px-3 py-1.5 transition-colors hover:bg-bg-2"
            style={{ color: "var(--fg-1)" }}
          >
            GitHub ↗
          </a>
          <Link
            href="/login"
            className="t-small border px-3 py-1.5 transition-colors hover:opacity-80"
            style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)", fontWeight: 500 }}
          >
            Sign in
          </Link>
        </div>
      </nav>

      {/* ── hero ── */}
      <section className="px-8 pt-20 pb-16 max-w-5xl mx-auto">
        <div className="flex items-center gap-2 mb-8">
          <span className="t-micro px-2 py-0.5 border border-line" style={{ color: "var(--fg-3)", fontFamily: "var(--font-jetbrains-mono)" }}>
            Open source · MIT licensed
          </span>
          <button
            onClick={copyInstall}
            className="t-micro px-2 py-0.5 border border-line flex items-center gap-1.5 transition-colors hover:bg-bg-2"
            style={{ color: "var(--fg-2)", fontFamily: "var(--font-jetbrains-mono)", background: "var(--bg-1)" }}
          >
            <span style={{ color: "var(--fg-3)" }}>$</span>
            pip install dqtlib
            <span style={{ color: "var(--fg-3)", marginLeft: 6 }}>{copied ? "✓ copied" : "⌘C"}</span>
          </button>
        </div>

        <h1 style={{ fontSize: "clamp(36px, 5.5vw, 68px)", fontWeight: 200, letterSpacing: "-0.03em", lineHeight: 1.06, color: "var(--fg-0)", maxWidth: 700 }}>
          Data quality that tells you <em style={{ fontStyle: "normal", color: "var(--accent)" }}>why</em>.
        </h1>

        <p className="t-body mt-5" style={{ color: "var(--fg-2)", maxWidth: 560, lineHeight: 1.75 }}>
          Statistical drift detection, column-level lineage, and causal discovery — for dbt, warehouses, and data lakes. In one Python library.
        </p>

        <div className="flex items-center gap-3 mt-8 flex-wrap">
          <button
            onClick={copyInstall}
            className="flex items-center gap-2 px-4 py-2.5 border transition-colors hover:opacity-80"
            style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)", fontWeight: 500 }}
          >
            <span style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 12 }}>pip install dqtlib</span>
            {copied ? " ✓" : " ⎘"}
          </button>
          <a
            href="https://github.com/anthropics/dqt"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-4 py-2.5 t-small border border-line transition-colors hover:bg-bg-2"
            style={{ color: "var(--fg-1)" }}
          >
            ★ Star on GitHub →
          </a>
        </div>
      </section>

      {/* ── stats band ── */}
      <section className="border-t border-b border-line" style={{ background: "var(--bg-1)" }}>
        <div className="grid mx-auto" style={{ maxWidth: 900, gridTemplateColumns: "repeat(4, 1fr)" }}>
          {[
            { value: "30+", label: "detector algorithms" },
            { value: "9+", label: "warehouse engines" },
            { value: "100k", label: "rows sampled / check" },
            { value: "MIT", label: "no vendor lock-in" },
          ].map((s, i) => (
            <div key={s.label} className="px-8 py-6 text-center" style={{ borderRight: i < 3 ? "1px solid var(--line)" : "none" }}>
              <p style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 30, fontWeight: 300, color: "var(--fg-0)", letterSpacing: "-0.02em" }}>
                {s.value}
              </p>
              <p className="t-micro mt-1" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── problem agitation ── */}
      <section id="why" className="px-8 py-20 max-w-5xl mx-auto">
        <p className="t-micro mb-3" style={{ color: "var(--fg-3)", letterSpacing: "0.12em", textTransform: "uppercase" }}>The hour after the alert</p>
        <h2 className="t-h1 mb-6" style={{ fontWeight: 300 }}>
          Most DQ tools tell you a row count dropped.<br />They don&apos;t tell you why.
        </h2>
        <div className="grid grid-cols-2 gap-12">
          <div className="space-y-4">
            <p className="t-body" style={{ color: "var(--fg-2)", lineHeight: 1.75 }}>
              You set a threshold. It fires. Slack lights up. Now you&apos;re bouncing between dbt docs, the warehouse, and your BI tool — trying to figure out which upstream model changed, whether the spike in nulls explains the dashboard regression, and whether this is worth waking the on-call engineer for.
            </p>
            <p className="t-body" style={{ color: "var(--fg-1)", lineHeight: 1.75 }}>
              <strong>dqt was built for the part that comes after the alert.</strong> It reads your dbt manifest, parses your warehouse SQL into a column-level lineage graph, runs 30+ statistical detectors against your tables, and discovers causal relationships across your metrics. So the next time something moves, you already know what moved it.
            </p>
          </div>
          <div className="space-y-3">
            <div className="p-4 border border-line" style={{ background: "var(--bg-1)" }}>
              <p className="t-micro mb-2" style={{ color: "var(--fg-3)", letterSpacing: "0.1em", textTransform: "uppercase" }}>Without dqt</p>
              <div className="space-y-2">
                <div className="flex items-start gap-2">
                  <span style={{ color: "var(--fail)" }}>✗</span>
                  <span className="t-small" style={{ color: "var(--fg-2)" }}>orders.amount null_fraction ≥ 0.05 — threshold exceeded</span>
                </div>
                <p className="t-micro pl-5" style={{ color: "var(--fg-3)" }}>Now what? Go dig through git log, dbt docs, warehouse history…</p>
              </div>
            </div>
            <div className="p-4 border" style={{ background: "var(--bg-1)", borderColor: "var(--accent)30" }}>
              <p className="t-micro mb-2" style={{ color: "var(--accent)", letterSpacing: "0.1em", textTransform: "uppercase" }}>With dqt</p>
              <div className="space-y-2">
                <div className="flex items-start gap-2">
                  <span style={{ color: "var(--fail)" }}>✗</span>
                  <span className="t-small" style={{ color: "var(--fg-1)" }}>orders.amount null_fraction = 12.4% (baseline 0.3%)</span>
                </div>
                <p className="t-small pl-5" style={{ color: "var(--fg-2)", lineHeight: 1.6 }}>
                  Causal trace: <span style={{ color: "var(--accent)", fontFamily: "var(--font-jetbrains-mono)" }}>stg_payments → orders → revenue</span>. Upstream model <span style={{ fontFamily: "var(--font-jetbrains-mono)" }}>stg_payments</span> introduced a schema break 6 hours ago. E-value = 3.2 (robust to confounders).
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── capabilities ── */}
      <section className="border-t border-line px-8 py-20" style={{ background: "var(--bg-1)" }}>
        <div className="max-w-5xl mx-auto">
          <p className="t-micro mb-3" style={{ color: "var(--fg-3)", letterSpacing: "0.12em", textTransform: "uppercase" }}>Four layers. One library.</p>
          <div className="grid grid-cols-2 gap-px mt-8" style={{ background: "var(--line)" }}>
            {CAPABILITIES.map((c) => (
              <div key={c.label} className="p-6 space-y-2" style={{ background: "var(--bg-1)", borderLeft: c.highlight ? "2px solid var(--accent)" : "2px solid transparent" }}>
                <p className="t-micro" style={{ color: c.highlight ? "var(--accent)" : "var(--fg-3)", letterSpacing: "0.1em", textTransform: "uppercase" }}>{c.label}</p>
                <h3 className="t-h3" style={{ color: "var(--fg-0)" }}>{c.slugline}</h3>
                <p className="t-small" style={{ color: "var(--fg-2)", lineHeight: 1.7 }}>{c.desc}</p>
                {c.mono && (
                  <p className="t-micro pt-2" style={{ color: "var(--fg-3)", fontFamily: "var(--font-jetbrains-mono)", lineHeight: 1.8 }}>{c.mono}</p>
                )}
                {c.highlight && (
                  <p className="t-micro pt-1" style={{ color: "var(--accent)" }}>The only DQ tool that ships causal discovery.</p>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── detector catalog ── */}
      <section className="border-t border-line px-8 py-16 max-w-5xl mx-auto">
        <p className="t-micro mb-6" style={{ color: "var(--fg-3)", letterSpacing: "0.12em", textTransform: "uppercase" }}>
          Detector catalog · {DETECTORS.length} algorithms
        </p>
        <div className="flex flex-wrap gap-x-4 gap-y-1.5">
          {DETECTORS.map((d) => (
            <span key={d} className="t-micro" style={{ color: "var(--fg-2)", fontFamily: "var(--font-jetbrains-mono)" }}>{d}</span>
          ))}
        </div>
      </section>

      {/* ── code proof ── */}
      <section id="code" className="border-t border-line px-8 py-20" style={{ background: "var(--bg-1)" }}>
        <div className="max-w-5xl mx-auto">
          <p className="t-micro mb-3" style={{ color: "var(--fg-3)", letterSpacing: "0.12em", textTransform: "uppercase" }}>Three lines to your first check.</p>
          <h2 className="t-h1 mb-8" style={{ fontWeight: 300 }}>Runs in notebooks. Runs in CI.<br />No server required.</h2>

          <div className="border border-line" style={{ background: "var(--bg-0)" }}>
            <div className="flex items-center border-b border-line" style={{ background: "var(--bg-2)" }}>
              {(["python", "yaml", "cli"] as TabKey[]).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className="px-4 py-2 t-small border-b-2 transition-colors"
                  style={{
                    borderBottomColor: tab === t ? "var(--accent)" : "transparent",
                    color: tab === t ? "var(--fg-0)" : "var(--fg-3)",
                    fontFamily: "var(--font-jetbrains-mono)",
                  }}
                >
                  {t}
                </button>
              ))}
            </div>
            <pre
              className="p-6 overflow-x-auto"
              style={{
                fontFamily: "var(--font-jetbrains-mono)",
                fontSize: 12,
                lineHeight: 1.7,
                color: "var(--fg-1)",
                margin: 0,
              }}
            >
              {tabContent[tab]}
            </pre>
          </div>

          <p className="t-small mt-4" style={{ color: "var(--fg-2)", lineHeight: 1.7 }}>
            Runs in notebooks. Runs in CI. Runs as one Python task in Airflow, Dagster, or Prefect.{" "}
            <strong style={{ color: "var(--fg-1)" }}>No server required.</strong> The optional FastAPI service and dashboard are there when you want them — and stay out of the way when you don&apos;t.
          </p>
        </div>
      </section>

      {/* ── comparison table ── */}
      <section id="compare" className="border-t border-line px-8 py-20 max-w-5xl mx-auto">
        <p className="t-micro mb-3" style={{ color: "var(--fg-3)", letterSpacing: "0.12em", textTransform: "uppercase" }}>Where dqt sits.</p>
        <h2 className="t-h1 mb-2" style={{ fontWeight: 300 }}>We borrowed the best ideas.<br />Then shipped the parts they don&apos;t have.</h2>
        <p className="t-small mb-8" style={{ color: "var(--fg-2)" }}>
          Causal discovery isn&apos;t a nice-to-have — it&apos;s the difference between <em>&ldquo;orders are down&rdquo;</em> and <em>&ldquo;orders are down because the EU marketing-spend job missed its 06:00 run.&rdquo;</em>
        </p>

        <div className="border border-line overflow-x-auto" style={{ background: "var(--bg-1)" }}>
          <table className="w-full" style={{ borderCollapse: "collapse", minWidth: 640 }}>
            <thead>
              <tr style={{ background: "var(--bg-2)" }}>
                <th className="px-4 py-3 text-left t-micro" style={{ color: "var(--fg-3)", fontWeight: 400, letterSpacing: "0.1em", textTransform: "uppercase" }}>Capability</th>
                {[
                  { key: "dqt", label: "dqt", accent: true },
                  { key: "gx", label: "Great Expectations", accent: false },
                  { key: "soda", label: "Soda", accent: false },
                  { key: "elementary", label: "Elementary", accent: false },
                  { key: "dataplex", label: "Dataplex", accent: false },
                ].map((c) => (
                  <th key={c.key} className="px-4 py-3 text-center t-micro" style={{ color: c.accent ? "var(--accent)" : "var(--fg-3)", fontWeight: c.accent ? 600 : 400, letterSpacing: "0.08em" }}>
                    {c.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {COMPARISON.map((row, i) => (
                <tr key={row.label} className="border-t border-line" style={{ background: i % 2 === 0 ? "var(--bg-1)" : "var(--bg-0)" }}>
                  <td className="px-4 py-2.5 t-small" style={{ color: "var(--fg-1)" }}>{row.label}</td>
                  {[row.dqt, row.gx, row.soda, row.elementary, row.dataplex].map((v, j) => (
                    <td key={j} className="px-4 py-2.5 text-center t-small">
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
      <section className="border-t border-line px-8 py-16" style={{ background: "var(--bg-1)" }}>
        <div className="max-w-5xl mx-auto">
          <p className="t-micro mb-3" style={{ color: "var(--fg-3)", letterSpacing: "0.12em", textTransform: "uppercase" }}>Drop it in next to the tools you already use.</p>
          <div className="mt-6 space-y-0 border border-line" style={{ background: "var(--bg-0)" }}>
            {INTEGRATIONS.map((item, i) => (
              <div key={i} className="flex items-center gap-6 px-5 py-3 border-b border-line last:border-0">
                <span className="t-small" style={{ color: "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)", minWidth: 240 }}>{item.name}</span>
                <span className="t-small" style={{ color: "var(--fg-2)" }}>{item.note}</span>
              </div>
            ))}
          </div>
          <p className="t-small mt-5" style={{ color: "var(--fg-2)" }}>
            You don&apos;t replace anything to adopt dqt. You point it at the warehouse you already have.
          </p>
        </div>
      </section>

      {/* ── final CTA ── */}
      <section className="border-t border-line px-8 py-24 text-center" style={{ background: "var(--bg-0)" }}>
        <h2 className="t-h1 mb-3" style={{ fontWeight: 300 }}>
          Install it. Point it at your warehouse.<br />See your first incident in five minutes.
        </h2>

        <button
          onClick={copyInstall}
          className="flex items-center gap-3 mx-auto mt-8 px-6 py-3 border border-line transition-colors hover:bg-bg-2"
          style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 14, color: "var(--fg-0)", background: "var(--bg-1)" }}
        >
          <span style={{ color: "var(--fg-3)" }}>$</span>
          pip install dqtlib
          <span style={{ color: "var(--fg-3)" }}>{copied ? "✓ copied" : "⎘"}</span>
        </button>

        <div className="flex items-center justify-center gap-3 mt-6 flex-wrap">
          <a
            href="https://github.com/anthropics/dqt"
            target="_blank"
            rel="noopener noreferrer"
            className="px-5 py-2.5 t-small border border-line transition-colors hover:bg-bg-2"
            style={{ color: "var(--fg-1)" }}
          >
            ★ Star on GitHub →
          </a>
          <Link
            href="/login"
            className="px-5 py-2.5 t-small border transition-colors hover:opacity-80"
            style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)", fontWeight: 500 }}
          >
            Open the dashboard →
          </Link>
        </div>

        <p className="t-micro mt-8" style={{ color: "var(--fg-3)" }}>
          Open source. MIT licensed. Python 3.12+. No telemetry. No signup. No credit card.
        </p>
      </section>

      {/* ── footer ── */}
      <footer className="border-t border-line px-8 py-4 flex items-center justify-between" style={{ background: "var(--bg-1)" }}>
        <span style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 14, fontWeight: 300, letterSpacing: "-0.05em", color: "var(--accent)" }}>
          dqt
        </span>
        <div className="flex items-center gap-6">
          <a href="https://github.com/anthropics/dqt" target="_blank" rel="noopener noreferrer" className="t-small transition-opacity hover:opacity-70" style={{ color: "var(--fg-3)" }}>
            GitHub
          </a>
          <span className="t-small" style={{ color: "var(--fg-3)" }}>MIT License</span>
          <span className="t-small" style={{ color: "var(--fg-3)" }}>Python 3.12+</span>
        </div>
      </footer>
    </div>
  );
}
