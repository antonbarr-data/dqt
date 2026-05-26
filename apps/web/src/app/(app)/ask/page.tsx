"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { Send, Loader2, MessageSquare, ArrowUpRight } from "lucide-react";

interface ClarifyOption {
  metric_fqn: string;
  display_name: string;
  confidence: number;
}

type MessageRole = "user" | "assistant";

interface ChatMessage {
  id: string;
  role: MessageRole;
  type: "text" | "answer" | "disambiguation" | "loading";
  content?: string;
  // answer fields
  intent?: string;
  metric_fqn?: string;
  display_name?: string;
  window_days?: number;
  // disambiguation fields
  message?: string;
  options?: ClarifyOption[];
  // original question for clarify calls
  question?: string;
}

const EXAMPLE_PROMPTS = [
  "Why is revenue down this week?",
  "What drove GMV growth last month?",
  "Are there any anomalies in fulfillment rate?",
  "Which metrics are trending down?",
];

export default function AskPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function submit(question?: string) {
    const q = (question ?? input).trim();
    if (!q || loading) return;
    setInput("");

    const id = Math.random().toString(36).slice(2);
    setMessages((prev) => [
      ...prev,
      { id: `u-${id}`, role: "user", type: "text", content: q },
      { id: `a-${id}`, role: "assistant", type: "loading", question: q },
    ]);
    setLoading(true);

    try {
      const resp = await fetch("/api/v1/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      const data = await resp.json();
      setMessages((prev) =>
        prev.map((m) =>
          m.id === `a-${id}`
            ? { ...m, ...data, type: data.type ?? "answer", question: q }
            : m
        )
      );
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === `a-${id}`
            ? { ...m, type: "disambiguation", message: "Request failed. Please try again.", options: [] }
            : m
        )
      );
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  async function clarify(msgId: string, question: string, fqn: string) {
    setMessages((prev) =>
      prev.map((m) => m.id === msgId ? { ...m, type: "loading" } : m)
    );
    try {
      const resp = await fetch("/api/v1/ask/clarify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, chosen_fqn: fqn }),
      });
      const data = await resp.json();
      setMessages((prev) =>
        prev.map((m) => m.id === msgId ? { ...m, ...data } : m)
      );
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === msgId
            ? { ...m, type: "disambiguation", message: "Request failed.", options: [] }
            : m
        )
      );
    }
  }

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  const isEmpty = messages.length === 0;

  return (
    <div className="flex flex-col" style={{ height: "100%", background: "var(--bg-0)" }}>

      {/* Empty state */}
      {isEmpty && (
        <div className="flex-1 flex flex-col items-center justify-center px-6" style={{ paddingBottom: 80 }}>
          <MessageSquare size={28} strokeWidth={1} style={{ color: "var(--fg-3)", marginBottom: 16 }} />
          <p className="t-h3 mb-1" style={{ color: "var(--fg-0)", fontWeight: 300 }}>Ask dqt anything</p>
          <p className="t-small mb-8" style={{ color: "var(--fg-3)" }}>
            Natural language questions about your metrics, incidents, and data quality
          </p>
          <div className="grid gap-2" style={{ gridTemplateColumns: "1fr 1fr", maxWidth: 520, width: "100%" }}>
            {EXAMPLE_PROMPTS.map((p) => (
              <button
                key={p}
                onClick={() => submit(p)}
                className="text-left px-4 py-3 border border-line t-small transition-colors hover:bg-bg-2 hover:border-line-3"
                style={{ background: "var(--bg-1)", color: "var(--fg-1)", lineHeight: 1.4 }}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      {!isEmpty && (
        <div className="flex-1 overflow-y-auto px-6 py-6" style={{ maxWidth: 720, width: "100%", margin: "0 auto" }}>
          <div className="space-y-6">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={msg.role === "user" ? "flex justify-end" : "flex justify-start"}
              >
                {msg.role === "user" ? (
                  <div
                    className="t-small px-4 py-3 max-w-md"
                    style={{
                      background: "var(--accent-bg)",
                      color: "var(--fg-0)",
                      border: "1px solid var(--accent)",
                      lineHeight: 1.5,
                    }}
                  >
                    {msg.content}
                  </div>
                ) : (
                  <div className="flex-1 max-w-xl">
                    <AssistantBubble msg={msg} onClarify={clarify} />
                  </div>
                )}
              </div>
            ))}
          </div>
          <div ref={bottomRef} />
        </div>
      )}

      {/* Input */}
      <div
        className="px-6 py-4 border-t border-line"
        style={{ background: "var(--bg-0)", maxWidth: 720, width: "100%", margin: "0 auto", alignSelf: "stretch" }}
      >
        <div
          className="flex items-end gap-3 border border-line transition-colors focus-within:border-accent"
          style={{ background: "var(--bg-1)" }}
        >
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask about your data..."
            rows={1}
            className="flex-1 px-4 py-3 t-small bg-transparent outline-none resize-none"
            style={{
              color: "var(--fg-0)",
              minHeight: 44,
              maxHeight: 160,
              lineHeight: 1.5,
            }}
          />
          <button
            onClick={() => submit()}
            disabled={loading || !input.trim()}
            className="flex items-center justify-center m-2 transition-colors disabled:opacity-30"
            style={{
              width: 32,
              height: 32,
              background: input.trim() ? "var(--accent)" : "var(--bg-2)",
              color: input.trim() ? "var(--bg-0)" : "var(--fg-3)",
              flexShrink: 0,
            }}
            title="Send (Enter)"
          >
            {loading ? (
              <Loader2 size={14} strokeWidth={2} className="animate-spin" />
            ) : (
              <Send size={14} strokeWidth={1.6} />
            )}
          </button>
        </div>
        <p className="t-micro mt-1.5" style={{ color: "var(--fg-3)" }}>
          Enter to send, Shift+Enter for newline
        </p>
      </div>
    </div>
  );
}

function AssistantBubble({
  msg,
  onClarify,
}: {
  msg: ChatMessage;
  onClarify: (id: string, question: string, fqn: string) => void;
}) {
  if (msg.type === "loading") {
    return (
      <div className="flex items-center gap-2 py-2" style={{ color: "var(--fg-3)" }}>
        <Loader2 size={13} strokeWidth={1.6} className="animate-spin" />
        <span className="t-small">Analyzing...</span>
      </div>
    );
  }

  if (msg.type === "answer" && msg.metric_fqn && msg.metric_fqn !== "*") {
    return (
      <div
        className="border border-line p-4 space-y-3"
        style={{ background: "var(--bg-1)" }}
      >
        <p className="t-small" style={{ color: "var(--fg-1)", lineHeight: 1.5 }}>
          Showing insight for{" "}
          <span className="font-mono" style={{ color: "var(--accent)" }}>{msg.display_name}</span>
          {" "}over the last {msg.window_days} days.
        </p>
        <div className="flex items-center gap-4 pt-1">
          <Link
            href={`/metrics/${encodeURIComponent(msg.metric_fqn!)}` as never}
            className="t-small flex items-center gap-1.5 hover:opacity-80 transition-opacity"
            style={{ color: "var(--accent)" }}
          >
            Open metric insight
            <ArrowUpRight size={12} strokeWidth={1.6} />
          </Link>

        </div>
      </div>
    );
  }

  if (msg.type === "answer" && msg.intent === "list") {
    return (
      <div className="border border-line p-4" style={{ background: "var(--bg-1)" }}>
        <p className="t-small" style={{ color: "var(--fg-1)", lineHeight: 1.5 }}>
          See all metric movements over the last {msg.window_days} days on the{" "}
          <Link href="/overview" className="hover:underline" style={{ color: "var(--accent)" }}>
            Overview
          </Link>.
        </p>
      </div>
    );
  }

  if (msg.type === "disambiguation") {
    return (
      <div className="border border-line p-4 space-y-3" style={{ background: "var(--bg-1)" }}>
        <p className="t-small" style={{ color: "var(--fg-2)", lineHeight: 1.5 }}>
          {msg.message || "Which metric did you mean?"}
        </p>
        {msg.options && msg.options.length > 0 ? (
          <div className="space-y-1.5">
            {msg.options.map((opt) => (
              <button
                key={opt.metric_fqn}
                onClick={() => onClarify(msg.id, msg.question || "", opt.metric_fqn)}
                className="w-full text-left px-3 py-2.5 border border-line hover:border-accent transition-colors"
                style={{ background: "var(--bg-2)" }}
              >
                <span className="t-small" style={{ color: "var(--fg-0)" }}>{opt.display_name}</span>
                <span className="t-micro font-mono ml-2" style={{ color: "var(--fg-3)" }}>{opt.metric_fqn}</span>
              </button>
            ))}
          </div>
        ) : (
          <p className="t-small" style={{ color: "var(--fg-3)" }}>
            No matching metrics found.
          </p>
        )}
      </div>
    );
  }

  return null;
}
