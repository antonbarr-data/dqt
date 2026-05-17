"use client";

import { useState } from "react";
import Link from "next/link";
import { SubscribeButton } from "@/components/subscriptions/subscribe-button";

interface ClarifyOption {
  metric_fqn: string;
  display_name: string;
  confidence: number;
}

interface ConversationEntry {
  id: string;
  question: string;
  type: "answer" | "disambiguation" | "loading";
  intent?: string;
  metric_fqn?: string;
  display_name?: string;
  window_days?: number;
  message?: string;
  options?: ClarifyOption[];
}

export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<ConversationEntry[]>([]);
  const [loading, setLoading] = useState(false);

  async function submit() {
    if (!question.trim() || loading) return;
    const q = question;
    setQuestion("");
    const id = Math.random().toString(36).slice(2);
    setHistory(h => [...h, { id, question: q, type: "loading" }]);
    setLoading(true);
    try {
      const resp = await fetch("/api/v1/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      const data = await resp.json();
      setHistory(h => h.map(e => e.id === id ? { ...e, ...data, question: q } : e));
    } catch {
      setHistory(h => h.map(e => e.id === id
        ? { ...e, type: "disambiguation", message: "Request failed. Please try again.", options: [] }
        : e));
    } finally {
      setLoading(false);
    }
  }

  async function clarify(entryId: string, entryQuestion: string, fqn: string) {
    setHistory(h => h.map(e => e.id === entryId ? { ...e, type: "loading" } : e));
    const resp = await fetch("/api/v1/ask/clarify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: entryQuestion, chosen_fqn: fqn }),
    });
    const data = await resp.json();
    setHistory(h => h.map(e => e.id === entryId ? { ...e, ...data } : e));
  }

  return (
    <div className="p-6 max-w-2xl">
      <div className="mb-6">
        <h1 className="t-h1" style={{ color: "var(--fg-0)" }}>Ask</h1>
        <p className="t-small mt-1" style={{ color: "var(--fg-3)" }}>
          Natural language questions about your metrics
        </p>
      </div>
      <div className="flex gap-2 mb-8">
        <input
          value={question}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") submit(); }}
          placeholder="Why is revenue down this week?"
          className="flex-1 border border-line px-3 py-2 t-small bg-transparent outline-none focus:border-accent transition-colors"
          style={{ color: "var(--fg-0)" }}
        />
        <button
          onClick={submit}
          disabled={loading || !question.trim()}
          className="px-4 py-2 t-small border border-line hover:border-accent transition-colors disabled:opacity-40"
          style={{ color: "var(--fg-1)", background: "var(--bg-1)" }}
        >
          Ask
        </button>
      </div>
      <div className="space-y-6">
        {history.map(entry => (
          <div key={entry.id}>
            <p className="t-small font-medium mb-2" style={{ color: "var(--fg-0)" }}>{entry.question}</p>
            {entry.type === "loading" && (
              <p className="t-small" style={{ color: "var(--fg-3)" }}>Resolving...</p>
            )}
            {entry.type === "answer" && entry.metric_fqn && entry.metric_fqn !== "*" && (
              <div className="border border-line p-4" style={{ background: "var(--bg-1)" }}>
                <p className="t-small mb-1" style={{ color: "var(--fg-1)" }}>
                  Showing insight for <span className="font-mono" style={{ color: "var(--accent)" }}>{entry.display_name}</span>
                  {" "}over the last {entry.window_days} days.
                </p>
                <div className="flex items-center gap-4 mt-2">
                  <Link href={`/metrics/${encodeURIComponent(entry.metric_fqn!)}`}
                        className="t-small hover:underline" style={{ color: "var(--accent)" }}>
                    Open metric insight page
                  </Link>
                  <SubscribeButton metricFqn={entry.metric_fqn!} />
                </div>
              </div>
            )}
            {entry.type === "answer" && entry.intent === "list" && (
              <div className="border border-line p-4" style={{ background: "var(--bg-1)" }}>
                <p className="t-small" style={{ color: "var(--fg-1)" }}>
                  See all metric movements over the last {entry.window_days} days on the{" "}
                  <Link href="/" className="hover:underline" style={{ color: "var(--accent)" }}>Today feed</Link>.
                </p>
              </div>
            )}
            {entry.type === "disambiguation" && (
              <div className="border border-line p-4" style={{ background: "var(--bg-1)" }}>
                <p className="t-small mb-3" style={{ color: "var(--fg-2)" }}>
                  {entry.message || "Which metric did you mean?"}
                </p>
                {entry.options && entry.options.length > 0 ? (
                  <div className="space-y-2">
                    {entry.options.map(opt => (
                      <button
                        key={opt.metric_fqn}
                        onClick={() => clarify(entry.id, entry.question, opt.metric_fqn)}
                        className="w-full text-left px-3 py-2 border border-line hover:border-accent transition-colors"
                        style={{ background: "var(--bg-2)" }}
                      >
                        <span className="t-small" style={{ color: "var(--fg-0)" }}>{opt.display_name}</span>
                        <span className="t-micro font-mono ml-2" style={{ color: "var(--fg-3)" }}>{opt.metric_fqn}</span>
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="t-small" style={{ color: "var(--fg-3)" }}>
                    No matching metrics found. Try the{" "}
                    <Link href="/search" className="hover:underline" style={{ color: "var(--accent)" }}>search page</Link>.
                  </p>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
