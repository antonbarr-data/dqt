"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

interface ClarifyOption {
  metric_fqn: string;
  display_name: string;
  confidence: number;
}

interface AskResponse {
  type: "answer" | "disambiguation";
  intent?: string;
  metric_fqn?: string;
  display_name?: string;
  window_days?: number;
  message?: string;
  options?: ClarifyOption[];
}

interface AskModalProps {
  open: boolean;
  onClose: () => void;
}

export function AskModal({ open, onClose }: AskModalProps) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<AskResponse | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  useEffect(() => {
    if (open) {
      setQuestion("");
      setResponse(null);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    if (open) document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  async function submit(q: string) {
    if (!q.trim()) return;
    setLoading(true);
    setResponse(null);
    try {
      const resp = await fetch("/api/v1/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      const data: AskResponse = await resp.json();
      if (data.type === "answer" && data.metric_fqn && data.metric_fqn !== "*") {
        onClose();
        router.push(`/metrics/${encodeURIComponent(data.metric_fqn)}`);
        return;
      }
      setResponse(data);
    } finally {
      setLoading(false);
    }
  }

  async function clarify(fqn: string) {
    setLoading(true);
    try {
      const resp = await fetch("/api/v1/ask/clarify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, chosen_fqn: fqn }),
      });
      const data: AskResponse = await resp.json();
      if (data.type === "answer" && data.metric_fqn) {
        onClose();
        router.push(`/metrics/${encodeURIComponent(data.metric_fqn)}`);
      } else {
        setResponse(data);
      }
    } finally {
      setLoading(false);
    }
  }

  if (!open) return null;

  return (
    <>
      <div className="fixed inset-0 z-40" style={{ background: "rgba(0,0,0,0.5)" }} onClick={onClose} />
      <div
        className="fixed z-50 top-1/4 left-1/2 -translate-x-1/2 w-full max-w-xl"
        style={{ background: "var(--bg-1)", border: "1px solid var(--line)", boxShadow: "0 8px 40px rgba(0,0,0,0.4)" }}
      >
        <div className="flex items-center border-b border-line px-4 py-3 gap-3">
          <span className="t-small font-mono" style={{ color: "var(--accent)" }}>ask</span>
          <input
            ref={inputRef}
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") submit(question); }}
            placeholder="Why is revenue down this week?"
            className="flex-1 bg-transparent t-small outline-none"
            style={{ color: "var(--fg-0)" }}
          />
          {loading && <span className="t-micro" style={{ color: "var(--fg-3)" }}>...</span>}
        </div>
        {response?.type === "disambiguation" && (
          <div className="p-4">
            <p className="t-small mb-3" style={{ color: "var(--fg-2)" }}>
              {response.message || "Which metric did you mean?"}
            </p>
            {response.options && response.options.length > 0 ? (
              <div className="space-y-2">
                {response.options.map(opt => (
                  <button
                    key={opt.metric_fqn}
                    onClick={() => clarify(opt.metric_fqn)}
                    className="w-full text-left px-3 py-2 border border-line hover:border-accent transition-colors"
                    style={{ background: "var(--bg-2)" }}
                  >
                    <span className="t-small" style={{ color: "var(--fg-0)" }}>{opt.display_name}</span>
                    <span className="t-micro font-mono ml-2" style={{ color: "var(--fg-3)" }}>{opt.metric_fqn}</span>
                  </button>
                ))}
              </div>
            ) : (
              <p className="t-small" style={{ color: "var(--fg-3)" }}>No matching metrics found.</p>
            )}
          </div>
        )}
        {!response && !loading && (
          <div className="px-4 py-3">
            <p className="t-micro" style={{ color: "var(--fg-3)" }}>
              Try: &quot;Why is revenue down this week?&quot; or &quot;What moved significantly yesterday?&quot;
            </p>
          </div>
        )}
      </div>
    </>
  );
}
