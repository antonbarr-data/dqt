"use client";

import { useEffect, useRef } from "react";

interface AuditDrawerProps {
  open: boolean;
  sentenceId: string | null;
  citations: Record<string, string[]>;
  onClose: () => void;
}

export function AuditDrawer({ open, sentenceId, citations, onClose }: AuditDrawerProps) {
  const drawerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onKey(e: KeyboardEvent) { if (e.key === "Escape") onClose(); }
    if (open) document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const evidenceRowIds = sentenceId ? (citations[sentenceId] ?? []) : [];

  return (
    <>
      <div
        className="fixed inset-0 z-40"
        style={{ background: "rgba(0,0,0,0.4)" }}
        onClick={onClose}
      />
      <div
        ref={drawerRef}
        className="fixed top-0 right-0 h-full z-50 flex flex-col"
        style={{ width: 360, background: "var(--bg-1)", borderLeft: "1px solid var(--line)",
                 boxShadow: "-4px 0 24px rgba(0,0,0,0.3)" }}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-line">
          <span className="t-small font-medium" style={{ color: "var(--fg-0)" }}>Audit trail</span>
          <button onClick={onClose} className="t-small hover:opacity-70"
                  style={{ color: "var(--fg-3)" }}>x</button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          {sentenceId && (
            <p className="t-micro mb-4" style={{ color: "var(--fg-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
              Sentence {sentenceId}
            </p>
          )}
          {evidenceRowIds.length === 0 ? (
            <p className="t-small" style={{ color: "var(--fg-3)" }}>
              No evidence rows cited for this sentence. This sentence was generated from the template fallback.
            </p>
          ) : (
            <div className="space-y-3">
              <p className="t-small mb-3" style={{ color: "var(--fg-2)" }}>
                {evidenceRowIds.length} evidence row{evidenceRowIds.length > 1 ? "s" : ""} cited:
              </p>
              {evidenceRowIds.map((rowId) => (
                <div key={rowId} className="border border-line p-3"
                     style={{ background: "var(--bg-2)", fontFamily: "var(--font-jetbrains-mono)" }}>
                  <span className="t-micro font-mono" style={{ color: "var(--accent)" }}>{rowId}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
