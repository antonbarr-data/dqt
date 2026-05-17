import Link from "next/link";
import { Network } from "lucide-react";

export default function Page() {
  return (
    <main className="p-8 fade-in">
      <div className="flex items-center gap-3 mb-6">
        <Network size={18} strokeWidth={1.6} style={{ color: "var(--fg-2)" }} />
        <h1 className="t-h1" style={{ color: "var(--fg-0)" }}>Causality</h1>
      </div>
      <p className="t-body mb-4" style={{ color: "var(--fg-2)" }}>
        Causal discovery runs weekly. Review proposed edges before they enter the production DAG.
      </p>
      <Link
        href="/causal/review"
        className="inline-flex items-center gap-2 t-small px-4 py-2 border border-line hover:border-accent transition-colors"
        style={{ color: "var(--fg-1)", background: "var(--bg-1)" }}
      >
        Open reviewer queue
      </Link>
    </main>
  );
}
