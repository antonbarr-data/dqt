export default function MetricsPage() {
  return (
    <div className="p-6">
      <h1 className="t-h1 mb-2" style={{ color: "var(--fg-0)" }}>Metrics</h1>
      <p className="t-small mb-6" style={{ color: "var(--fg-2)" }}>
        The metric insight page is being rebuilt for v1.1. Full two-channel reconciliation,
        narrative explanations, and the Why Layer arrive with the next release.
      </p>
      <div className="border border-line p-8 text-center" style={{ background: "var(--bg-1)" }}>
        <p className="t-small font-mono mb-2" style={{ color: "var(--fg-3)" }}>v1.1.0 -- coming next</p>
        <p className="t-body" style={{ color: "var(--fg-1)" }}>
          Metric insight page with two-channel reconciliation
        </p>
        <p className="t-small mt-2" style={{ color: "var(--fg-3)" }}>
          In the meantime, explore metrics via the Datasets and Causality pages.
        </p>
      </div>
    </div>
  )
}
