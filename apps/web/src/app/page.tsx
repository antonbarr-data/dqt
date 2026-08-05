"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getToken } from "@/lib/auth";
import { DQT_VERSION } from "@/lib/version";

const GITHUB_URL = "https://github.com/antonbarr-data/dqt";
const REGISTRY_URL = "https://raw.githubusercontent.com/antonbarr-data/dqt/main/docs/registry.json";

const LOGO_TOOLTIP = "質 (shitsu) - quality, substance, the inner nature of a thing. The kanji points to what something truly is, not how it appears. dqt is meant to work the same way: concerned with the truth of the data, not its surface. The mark is also a quiet acknowledgment of a tradition I have learned much from - one in which quality is one of its most distinguishing characteristics, and craft and precision are understood to be the same thing. — Anton Barr";

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

const FALLBACK_DETECTORS = [
  // univariate outliers
  "mad_outlier_fraction", "double_mad_outlier_fraction", "zscore_outlier_fraction",
  "adjusted_boxplot_fraction", "auto_outlier", "iqr_fence", "grubbs", "generalized_esd",
  // multivariate outliers
  "isolation_forest_fraction", "mahalanobis_distance", "lof", "one_class_svm", "hbos", "ecod",
  // drift & distribution shift
  "ks_pvalue", "wasserstein_1", "psi", "kl_divergence", "js_divergence", "chi_square_drift",
  "outlier_fraction_drift", "mmd", "adwin",
  // time series anomalies
  "stl_residual_zscore", "cusum", "page_hinkley", "holt_winters", "prophet_anomaly", "bocpd", "matrix_profile",
  // associations & information theory
  "cramers_v", "mutual_information",
  // pattern
  "benford_law_fit",
  // extension points
  "callable_check", "remote_check",
];

const FALLBACK_CHECKS = [
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
  // validity
  "validity",
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
    label: "Google OKF / Apache Ossie · Semantic layer",
    slugline: "Point dqt at a repo. It imports the semantic layer.",
    desc: "Connect a Git repo of Google OKF bundles or Apache Ossie files. dqt walks the tree, an LLM extracts the datasets, columns, metrics, and playbooks, and you review and select what to import against a live source. Datasets, metrics, and disabled checks land automatically.",
    mono: "okf/tables/ · okf/metrics/ · ossie/*.yaml → datasets · metrics · checks",
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


type TabKey = "python" | "yaml" | "cli";

export default function RootPage() {
  const router = useRouter();
  const [tab, setTab] = useState<TabKey>("python");
  const [copied, setCopied] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [detectors, setDetectors] = useState<string[]>(FALLBACK_DETECTORS);
  const [checks, setChecks] = useState<string[]>(FALLBACK_CHECKS);
  const [nAdapters, setNAdapters] = useState<number>(2);

  useEffect(() => {
    if (!getToken()) return;
    // Redirect to top pinned item, or Sources if no pins
    try {
      const raw = localStorage.getItem("dqt-nav-pins");
      const pins: string[] = raw ? JSON.parse(raw) : [];
      const NAV_HREFS: Record<string, string> = {
        Overview: "/overview", Ask: "/ask", Sources: "/sources",
        Datasets: "/datasets", Checks: "/checks", Incidents: "/incidents",
        Tasks: "/tasks", Metrics: "/metrics", Causality: "/causality",
        Catalog: "/catalog", Policies: "/policies", Audit: "/audit",
        "On-call": "/oncall", Users: "/settings/users",
      };
      if (pins.length > 0 && NAV_HREFS[pins[0]]) {
        router.replace(NAV_HREFS[pins[0]] as never);
      } else {
        router.replace("/sources" as never);
      }
    } catch {
      router.replace("/sources" as never);
    }
  }, [router]);

  useEffect(() => {
    fetch(REGISTRY_URL)
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data.detectors) && data.detectors.length > 0) {
          setDetectors(data.detectors.map((d: { slug: string }) => d.slug));
        }
        if (Array.isArray(data.checks) && data.checks.length > 0) {
          setChecks(data.checks.map((c: { slug: string }) => c.slug));
        }
        if (typeof data.n_adapters === "number" && data.n_adapters > 0) {
          setNAdapters(data.n_adapters);
        }
      })
      .catch(() => { /* keep fallback data */ });
  }, []);

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
        className="flex items-center justify-between px-6 border-b border-line sticky top-0 z-20"
        style={{ height: 52, background: "var(--bg-1)" }}
      >
        <LogoMark size="nav" />

        {/* desktop links */}
        <div className="hidden md:flex items-center gap-8">
          <a href="#why" className="t-small transition-opacity hover:opacity-70" style={{ color: "var(--fg-1)" }}>Why dqt</a>
          <a href="#code" className="t-small transition-opacity hover:opacity-70" style={{ color: "var(--fg-1)" }}>Code</a>
          <a href="#start" className="t-small transition-opacity hover:opacity-70" style={{ color: "var(--fg-1)" }}>Get started</a>
          <a href="#about" className="t-small transition-opacity hover:opacity-70" style={{ color: "var(--fg-1)" }}>About</a>
        </div>

        {/* desktop CTAs */}
        <div className="hidden md:flex items-center gap-2">
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

        {/* mobile hamburger */}
        <button
          className="md:hidden flex flex-col justify-center items-center gap-1 p-2"
          onClick={() => setMenuOpen(o => !o)}
          aria-label="Toggle menu"
          style={{ color: "var(--fg-0)", background: "none", border: "none", cursor: "pointer" }}
        >
          {menuOpen ? (
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
              <line x1="4" y1="4" x2="16" y2="16" /><line x1="16" y1="4" x2="4" y2="16" />
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
              <line x1="3" y1="6" x2="17" y2="6" /><line x1="3" y1="10" x2="17" y2="10" /><line x1="3" y1="14" x2="17" y2="14" />
            </svg>
          )}
        </button>
      </nav>

      {/* mobile menu drawer */}
      {menuOpen && (
        <div
          className="md:hidden flex flex-col border-b border-line sticky top-[52px] z-10"
          style={{ background: "var(--bg-1)" }}
        >
          <a href="#why" onClick={() => setMenuOpen(false)} className="px-6 py-4 t-small border-b border-line" style={{ color: "var(--fg-1)" }}>Why dqt</a>
          <a href="#code" onClick={() => setMenuOpen(false)} className="px-6 py-4 t-small border-b border-line" style={{ color: "var(--fg-1)" }}>Code</a>
          <a href="#start" onClick={() => setMenuOpen(false)} className="px-6 py-4 t-small border-b border-line" style={{ color: "var(--fg-1)" }}>Get started</a>
          <a href="#about" onClick={() => setMenuOpen(false)} className="px-6 py-4 t-small border-b border-line" style={{ color: "var(--fg-1)" }}>About</a>
          <div className="flex gap-2 px-6 py-4">
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="t-small border border-line px-3 py-1.5"
              style={{ color: "var(--fg-0)" }}
            >
              GitHub ↗
            </a>
            <Link
              href="/login"
              onClick={() => setMenuOpen(false)}
              className="t-small border px-3 py-1.5"
              style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)", fontWeight: 600 }}
            >
              Sign in
            </Link>
          </div>
        </div>
      )}

      {/* ── hero ── */}
      <section className="px-4 md:px-8 pt-10 pb-8 max-w-5xl mx-auto">
        <div className="flex items-center gap-3 mb-5">
          <a
            href="https://github.com/antonbarr-data/dqt/blob/main/LICENSE"
            target="_blank"
            rel="noopener noreferrer"
            className="px-2.5 py-1 border t-small"
            style={{ color: "var(--fg-0)", borderColor: "var(--line-2)", background: "var(--bg-2)", fontFamily: "var(--font-jetbrains-mono)", fontSize: 11, textDecoration: "none" }}
          >
            Open source · MIT licensed
          </a>
          <a
            href="https://github.com/antonbarr-data/dqt/blob/main/docs/releases/README.md"
            target="_blank"
            rel="noopener noreferrer"
            className="px-2.5 py-1 border t-small"
            style={{ color: "var(--accent)", borderColor: "var(--line-2)", background: "var(--bg-2)", fontFamily: "var(--font-jetbrains-mono)", fontSize: 11, textDecoration: "none" }}
          >
            v{DQT_VERSION}
          </a>
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

        <h1 style={{ fontSize: "clamp(44px, 5.6vw, 78px)", fontWeight: 200, letterSpacing: "-0.03em", lineHeight: 1.05, color: "var(--fg-0)", maxWidth: 740 }}>
          Data Quality Tool for <em style={{ fontStyle: "normal", color: "var(--accent)" }}>Agentic BI</em>. The <em style={{ fontStyle: "normal", color: "var(--warn)" }}>what</em> and the <em style={{ fontStyle: "normal", color: "var(--fail)" }}>why</em>.
        </h1>

        <p className="mt-4" style={{ fontSize: 16, color: "var(--fg-1)", maxWidth: 620, lineHeight: 1.7 }}>
          Unifies your scattered data into <strong style={{ color: "#ffffff" }}>one source of truth</strong>. Upgrades your existing models, dashboards, and queries into a <strong style={{ color: "#ffffff" }}>causal semantic layer</strong> you didn&apos;t have to write. Picks up on <strong style={{ color: "#ffffff" }}>trends</strong> and surfaces <strong style={{ color: "#ffffff" }}>business insights</strong>, all wrapped in a quality harness that puts <strong style={{ color: "#ffffff" }}>guardrails on the AI</strong> so the reports it generates stay <strong style={{ color: "#ffffff" }}>on-spec</strong>.
        </p>

        <p className="mt-4" style={{ fontSize: 14, color: "var(--fg-1)", maxWidth: 620, lineHeight: 1.7, borderLeft: "2px solid var(--accent)", paddingLeft: 12 }}>
          Every other data quality tool tells you <em style={{ fontStyle: "normal", color: "var(--fg-0)" }}>that</em> a metric broke. dqt is the open, gap-free superset that also tells you <em style={{ fontStyle: "normal", color: "var(--accent)" }}>why</em> - the only one with a causal layer that Great Expectations, Soda, Elementary, Dataplex, and Monte Carlo lack.
        </p>

        <p className="mt-3 flex items-center gap-2 flex-wrap" style={{ fontSize: 12, color: "var(--fg-2)" }}>
          <span>Built for</span>
          <span className="px-2 py-0.5 border" style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 11, color: "var(--fg-0)", borderColor: "var(--line-2)", background: "var(--bg-2)" }}>ClickHouse</span>
          <span>and</span>
          <span className="px-2 py-0.5 border" style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 11, color: "var(--fg-0)", borderColor: "var(--line-2)", background: "var(--bg-2)" }}>BigQuery</span>
          <span>first.</span>
          <span style={{ color: "var(--line-2)" }}>·</span>
          <span className="px-2 py-0.5 border" style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 11, color: "var(--warn)", borderColor: "var(--warn)", background: "rgba(217,181,102,0.07)" }}>Snowflake · Databricks · others - WIP</span>
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: "var(--accent)", fontSize: 12, borderBottom: "1px solid rgba(157,208,176,0.4)", textDecoration: "none" }}
          >
            contributors welcome ↗
          </a>
        </p>


        <div className="mt-5 border-l-2 pl-4 py-1" style={{ borderColor: "var(--accent)", maxWidth: 560 }}>
          <p style={{ fontSize: 11, color: "var(--accent)", letterSpacing: "0.12em", textTransform: "uppercase", fontWeight: 500, marginBottom: 6 }}>
            New · Google OKF / Apache Ossie import
          </p>
          <p style={{ fontSize: 15, color: "var(--fg-0)", fontWeight: 400, lineHeight: 1.55, marginBottom: 8 }}>
            Your semantic layer already exists in an open format. dqt imports it.
          </p>
          <p style={{ fontSize: 13, color: "var(--fg-1)", lineHeight: 1.7, marginBottom: 10 }}>
            Connect a Git repo of{" "}
            <a href="https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing" target="_blank" rel="noopener noreferrer" style={{ color: "var(--fg-0)", borderBottom: "1px solid var(--line)" }}>Google OKF</a>{" "}
            bundles or{" "}
            <a href="https://ossie.apache.org" target="_blank" rel="noopener noreferrer" style={{ color: "var(--fg-0)", borderBottom: "1px solid var(--line)" }}>Apache Ossie</a>{" "}
            files. An LLM extracts datasets, metrics, and playbooks. You review and select what to import. No manual YAML authoring.
          </p>
          <a
            href="https://ossie.apache.org"
            target="_blank"
            rel="noopener noreferrer"
            style={{ fontSize: 12, color: "var(--fg-1)", textDecoration: "none" }}
            className="transition-opacity hover:opacity-70"
          >
            Built on Google OKF and Apache Ossie ↗
          </a>
        </div>

        <div className="flex items-center gap-3 mt-6 flex-wrap">
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
        <div className="grid grid-cols-2 md:grid-cols-4 mx-auto" style={{ maxWidth: 900 }}>
          {([
            { value: String(detectors.length), label: "detector algorithms", color: "var(--accent)", cls: "border-r border-b border-line md:border-b-0", href: `${GITHUB_URL}/tree/main/packages/dqt/src/dqt/algorithms` },
            { value: String(checks.length), label: "declarative checks", color: "var(--accent)", cls: "border-b border-line md:border-b-0 md:border-r", href: `${GITHUB_URL}/tree/main/packages/dqt/src/dqt/algorithms/basic` },
            { value: String(nAdapters), label: "warehouse engines", color: "var(--accent)", cls: "border-r border-line", href: `${GITHUB_URL}/tree/main/packages/dqt/src/dqt/adapters` },
            { value: "MIT", label: "no vendor lock-in", color: "var(--pass)", cls: "", href: `${GITHUB_URL}/blob/main/LICENSE` },
          ] as { value: string; label: string; color: string; cls: string; href: string }[]).map((s) => (
            <a key={s.label} href={s.href} target="_blank" rel="noopener noreferrer" className={`px-6 py-5 text-center block transition-opacity hover:opacity-70 ${s.cls}`} style={{ textDecoration: "none" }}>
              <p style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 32, fontWeight: 300, color: s.color, letterSpacing: "-0.03em" }}>
                {s.value}
              </p>
              <p style={{ fontSize: 10, color: "var(--fg-2)", letterSpacing: "0.1em", textTransform: "uppercase", marginTop: 4 }}>{s.label}</p>
            </a>
          ))}
        </div>
      </section>

      {/* ── problem agitation ── */}
      <section id="why" className="px-8 py-14 max-w-5xl mx-auto">
        <p style={{ fontSize: 10, color: "var(--fg-1)", letterSpacing: "0.14em", textTransform: "uppercase", marginBottom: 10 }}>The hour after the alert</p>
        <h2 style={{ fontSize: "clamp(28px, 3.5vw, 44px)", fontWeight: 300, letterSpacing: "-0.02em", lineHeight: 1.15, marginBottom: 24 }}>
          Most monitoring tools tell you a row count dropped.<br />They don&apos;t tell you why.
        </h2>
        <div className="grid grid-cols-2 gap-10">
          <div className="space-y-4">
            <p style={{ fontSize: 14, color: "var(--fg-1)", lineHeight: 1.75 }}>
              You set a threshold. It fires. Slack lights up. Now you&apos;re bouncing between dbt docs, the warehouse, and your BI tool — trying to figure out which upstream model changed, whether the spike in nulls explains the dashboard regression, and whether this is worth waking the on-call engineer for.
            </p>
            <p style={{ fontSize: 14, color: "var(--fg-0)", lineHeight: 1.75 }}>
              <strong>dqt was built for the part that comes after the alert.</strong> It reads your dbt manifest, parses your warehouse SQL into a column-level lineage graph, runs {detectors.length} statistical detectors and {checks.length} declarative checks, and discovers causal relationships across your metrics — so the next time something moves, you already know what moved it.
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
                <div style={{ paddingLeft: 20, marginTop: 4 }} className="space-y-1">
                  <p style={{ fontSize: 12, color: "var(--fg-2)", lineHeight: 1.5 }}>
                    <span style={{ color: "var(--fg-1)" }}>Lineage:</span> <span style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 11, color: "var(--accent)" }}>stg_payments → orders → revenue</span>. Schema break in <span style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 11 }}>stg_payments</span> 6h ago.
                  </p>
                  <p style={{ fontSize: 12, color: "var(--fg-2)", lineHeight: 1.5 }}>
                    <span style={{ color: "var(--fg-1)" }}>Causal candidate:</span> <span style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 11 }}>stg_payments → orders.amount</span> (E-value 3.2, pending human review).
                  </p>
                </div>
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
                  <p style={{ fontSize: 11, color: "var(--pass)", paddingTop: 4, fontWeight: 500 }}>The only data quality tool for Agentic BI that ships causal discovery.</p>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Google OKF / Apache Ossie import ── */}
      <section className="border-t border-line px-8 py-14 max-w-5xl mx-auto">
        <div className="grid grid-cols-2 gap-12 items-start">
          <div>
            <p style={{ fontSize: 10, color: "var(--fg-1)", letterSpacing: "0.14em", textTransform: "uppercase", marginBottom: 10 }}>
              <a href="https://ossie.apache.org" target="_blank" rel="noopener noreferrer" style={{ color: "var(--fg-1)", borderBottom: "1px solid var(--line)" }}>Google OKF and Apache Ossie</a>
            </p>
            <h2 style={{ fontSize: "clamp(24px, 3vw, 40px)", fontWeight: 300, letterSpacing: "-0.02em", lineHeight: 1.2, marginBottom: 16 }}>
              Your semantic layer<br />is already written<br />in an open format.
            </h2>
            <p style={{ fontSize: 14, color: "var(--fg-1)", lineHeight: 1.75, marginBottom: 12 }}>
              <a href="https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing" target="_blank" rel="noopener noreferrer" style={{ color: "var(--fg-0)", borderBottom: "1px solid var(--line)" }}>Google OKF</a> captures tables, metrics, and playbooks as markdown with YAML frontmatter. <a href="https://ossie.apache.org" target="_blank" rel="noopener noreferrer" style={{ color: "var(--fg-0)", borderBottom: "1px solid var(--line)" }}>Apache Ossie</a> is a vendor neutral semantic model. Both are just files in a Git repo.
            </p>
            <p style={{ fontSize: 14, color: "var(--fg-1)", lineHeight: 1.75, marginBottom: 20 }}>
              Point dqt at the repo. An LLM extracts every dataset, column, metric, and playbook, reconciles them against your live warehouse, and you review and select what to import. Datasets, metrics, and a set of disabled checks land automatically. No manual YAML authoring.
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
              { step: "1", label: "Author or clone a semantic repo", sub: "Google OKF bundles or Apache Ossie files in Git", color: "var(--fg-3)" },
              { step: "2", label: "Connect it to a source", sub: "dqt repo add <git-url> --source <id>", color: "var(--fg-3)" },
              { step: "3", label: "dqt extracts a proposal", sub: "an LLM normalises datasets, columns, metrics, and playbooks", color: "var(--accent)" },
              { step: "4", label: "Review and select what to import", sub: "reconciled against your live warehouse schema", color: "var(--accent)" },
              { step: "5", label: "Datasets, metrics, and checks land", sub: "checks created disabled, armed after review", color: "var(--pass)" },
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
            Three plugins turn Claude Code into a grounded data quality engineer that knows your warehouse, knows the dqt API, and can run checks from natural language.
          </p>

          <div className="grid grid-cols-3 gap-0 border border-line">
            {[
              {
                num: "1",
                badge: "Context7",
                href: "https://claude.com/plugins/context7",
                title: "Up-to-date dqt docs",
                desc: `Connects Claude Code to dqt's live documentation and source — all ${detectors.length + checks.length} detector and check slugs, the exact YAML schema, and adapter protocol. No training-data lag.`,
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
        <div className="mb-8">
          <p style={{ fontSize: 10, color: "var(--fg-1)", letterSpacing: "0.14em", textTransform: "uppercase", marginBottom: 10 }}>Full detector catalog</p>
          <p style={{ fontSize: 13, color: "var(--fg-1)", lineHeight: 1.7, maxWidth: 640 }}>
            Three distinct problem domains: <span style={{ color: "var(--fg-0)" }}>point outliers</span>, <span style={{ color: "var(--fg-0)" }}>distribution drift</span>, and <span style={{ color: "var(--fg-0)" }}>time-series anomalies</span>. For any given column you typically need one or two — <span style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 12 }}>auto_outlier_fraction</span> picks the right one automatically based on the data&apos;s distribution. Note: <span style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 12 }}>zscore_outlier_fraction</span> assumes normality — use MAD or double-MAD on real warehouse data.
          </p>
        </div>
        <div className="space-y-8">
          <div>
            <p style={{ fontSize: 10, color: "var(--fg-1)", letterSpacing: "0.14em", textTransform: "uppercase", marginBottom: 12 }}>
              Statistical &amp; ML algorithms · {detectors.length}
            </p>
            <div className="flex flex-wrap gap-x-3 gap-y-2">
              {detectors.map((d) => (
                <a
                  key={d}
                  href={`${GITHUB_URL}/blob/main/docs/algorithms/${d}.md`}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    fontSize: 11,
                    color: "var(--fg-0)",
                    fontFamily: "var(--font-jetbrains-mono)",
                    background: "var(--bg-2)",
                    border: "1px solid var(--line)",
                    padding: "2px 8px",
                    textDecoration: "none",
                  }}
                  className="transition-colors hover:border-accent hover:text-accent"
                >
                  {d}
                </a>
              ))}
            </div>
          </div>
          <div>
            <p style={{ fontSize: 10, color: "var(--fg-1)", letterSpacing: "0.14em", textTransform: "uppercase", marginBottom: 12 }}>
              Declarative checks · {checks.length}
            </p>
            <div className="flex flex-wrap gap-x-3 gap-y-2">
              {checks.map((d) => (
                <a
                  key={d}
                  href={`${GITHUB_URL}/blob/main/docs/algorithms/${d}.md`}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    fontSize: 11,
                    color: "var(--fg-1)",
                    fontFamily: "var(--font-jetbrains-mono)",
                    background: "var(--bg-1)",
                    border: "1px solid var(--line)",
                    padding: "2px 8px",
                    textDecoration: "none",
                  }}
                  className="transition-colors hover:border-accent hover:text-accent"
                >
                  {d}
                </a>
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

      {/* ── get started ── */}
      <section id="start" className="border-t border-line px-8 py-14 max-w-5xl mx-auto">
        <p style={{ fontSize: 10, color: "var(--fg-1)", letterSpacing: "0.14em", textTransform: "uppercase", marginBottom: 10 }}>From zero to first incident.</p>
        <h2 style={{ fontSize: "clamp(24px, 3vw, 40px)", fontWeight: 300, letterSpacing: "-0.02em", lineHeight: 1.2, marginBottom: 8 }}>
          Getting started
        </h2>
        <p style={{ fontSize: 14, color: "var(--fg-1)", lineHeight: 1.7, marginBottom: 32, maxWidth: 560 }}>
          Four steps. No database, no server. Runs in a notebook or a CI job — wherever Python runs.
        </p>

        <div className="space-y-0 border border-line" style={{ background: "var(--bg-1)" }}>
          {/* Step 1 */}
          <div className="border-b border-line p-6 grid grid-cols-[40px_1fr] gap-4 items-start">
            <div style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 11, color: "var(--accent)", fontWeight: 600, paddingTop: 2 }}>01</div>
            <div>
              <p style={{ fontSize: 13, fontWeight: 600, color: "var(--fg-0)", marginBottom: 6 }}>Install</p>
              <pre style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 12, color: "var(--fg-0)", background: "var(--bg-0)", border: "1px solid var(--line)", padding: "10px 14px", margin: 0, overflowX: "auto" }}>
{`pip install dqtlib`}
              </pre>
            </div>
          </div>

          {/* Step 2 */}
          <div className="border-b border-line p-6 grid grid-cols-[40px_1fr] gap-4 items-start">
            <div style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 11, color: "var(--accent)", fontWeight: 600, paddingTop: 2 }}>02</div>
            <div>
              <p style={{ fontSize: 13, fontWeight: 600, color: "var(--fg-0)", marginBottom: 6 }}>Run your first check</p>
              <pre style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 12, color: "var(--fg-0)", background: "var(--bg-0)", border: "1px solid var(--line)", padding: "10px 14px", margin: 0, overflowX: "auto", lineHeight: 1.75 }}>
{`from dqt import Runner, MemoryStore
from dqt.checks.models import Check
from dqt.adapters.local import LocalAdapter
import pandas as pd

df    = pd.read_csv("orders.csv")
store = MemoryStore()

check = Check(
    schema_name="public", table_name="orders",
    column_name="amount_usd",
    detector_slug="wasserstein_1",   # drift detection
)
result = Runner(store).run_in_memory(
    check,
    reference=df[df.date < "2024-01-01"],
    current  =df[df.date >= "2024-01-01"],
)
print(result.verdict, result.plain_english)`}
              </pre>
            </div>
          </div>

          {/* Step 3 */}
          <div className="border-b border-line p-6 grid grid-cols-[40px_1fr] gap-4 items-start">
            <div style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 11, color: "var(--accent)", fontWeight: 600, paddingTop: 2 }}>03</div>
            <div>
              <p style={{ fontSize: 13, fontWeight: 600, color: "var(--fg-0)", marginBottom: 6 }}>Read the result</p>
              <div className="grid grid-cols-3 gap-px mt-2" style={{ background: "var(--line)" }}>
                {[
                  { field: "verdict", value: "pass · warn · fail", note: "threshold decision" },
                  { field: "score", value: "0.3142", note: "raw metric (Wasserstein distance)" },
                  { field: "plain_english", value: '"Distance 0.31 — above warn threshold"', note: "human-readable summary" },
                ].map(({ field, value, note }) => (
                  <div key={field} className="p-4" style={{ background: "var(--bg-0)" }}>
                    <p style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 11, color: "var(--accent)", marginBottom: 4 }}>{field}</p>
                    <p style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 12, color: "var(--fg-0)", marginBottom: 4 }}>{value}</p>
                    <p style={{ fontSize: 11, color: "var(--fg-2)" }}>{note}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Step 4 */}
          <div className="p-6 grid grid-cols-[40px_1fr] gap-4 items-start">
            <div style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 11, color: "var(--accent)", fontWeight: 600, paddingTop: 2 }}>04</div>
            <div>
              <p style={{ fontSize: 13, fontWeight: 600, color: "var(--fg-0)", marginBottom: 6 }}>Open the dashboard</p>
              <pre style={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: 12, color: "var(--fg-0)", background: "var(--bg-0)", border: "1px solid var(--line)", padding: "10px 14px", margin: 0, marginBottom: 10, overflowX: "auto" }}>
{`pip install "dqtlib[dashboard]"  # adds FastAPI + uvicorn
dqt dashboard --port 8080
# → http://127.0.0.1:8080`}
              </pre>
              <p style={{ fontSize: 13, color: "var(--fg-1)", lineHeight: 1.7 }}>
                Checks, column distribution profiles, and Granger causality inference — all in one place. No signup, no cloud, no persistent state beyond the process.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-6 flex items-center gap-4">
          <a
            href="https://github.com/antonbarr-data/dqt/blob/main/docs/getting-started.md"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-5 py-3 border transition-colors hover:opacity-80"
            style={{ background: "var(--accent)", color: "var(--bg-0)", borderColor: "var(--accent)", fontWeight: 600, fontSize: 13, textDecoration: "none" }}
          >
            Read the full guide →
          </a>
          <a
            href="https://github.com/antonbarr-data/dqt/blob/main/docs/api/detectors.md"
            target="_blank"
            rel="noopener noreferrer"
            className="t-small border border-line px-4 py-2.5 transition-colors hover:bg-bg-2"
            style={{ color: "var(--fg-0)", textDecoration: "none" }}
          >
            All {detectors.length + checks.length} checks & detectors →
          </a>
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

      {/* ── about ── */}
      <section id="about" className="border-t border-line px-8 py-10" style={{ background: "var(--bg-0)" }}>
        <div className="mx-auto" style={{ maxWidth: 700 }}>
          <p style={{ fontSize: 13, color: "var(--fg-2)", letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 12 }}>About the author</p>
          <p style={{ fontSize: 15, color: "var(--fg-1)", lineHeight: 1.75 }}>
            <a href="https://www.linkedin.com/in/antonbar/" target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent)", textDecoration: "none" }} className="hover:opacity-70">Anton Barr</a>
            {" "}is an engineer and data geek with 25+ years building data systems. A student of <span style={{ color: "var(--accent)" }}>質</span> (shitsu): quality, substance, the inner nature of a thing. <span style={{ color: "var(--accent)", fontFamily: "var(--font-jetbrains-mono)", fontWeight: 500, letterSpacing: "-0.05em" }}>dqt</span> is a personal project built by a practitioner who believes craft and precision are the same thing - and got tired of tools that answer <em>what</em> but never <em>why</em>.
          </p>
        </div>
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
