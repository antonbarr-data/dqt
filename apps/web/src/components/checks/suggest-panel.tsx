"use client"

import { useState, useEffect } from "react"

interface Suggestion {
  detector_slug: string
  params: Record<string, unknown>
  rationale: string
  confidence: number
}

export function SuggestPanel({
  datasetId,
  column,
}: {
  datasetId: string
  column: string
}) {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [loading, setLoading] = useState(true)
  const [accepted, setAccepted] = useState<Set<string>>(new Set())

  useEffect(() => {
    fetch(
      `/api/v1/datasets/${encodeURIComponent(datasetId)}/columns/${encodeURIComponent(column)}/suggest`
    )
      .then((r) => (r.ok ? r.json() : []))
      .then(setSuggestions)
      .catch(() => setSuggestions([]))
      .finally(() => setLoading(false))
  }, [datasetId, column])

  if (loading) {
    return (
      <div className="px-4 py-3 t-small" style={{ color: "var(--fg-3)" }}>
        Analyzing column...
      </div>
    )
  }

  if (suggestions.length === 0) {
    return (
      <div className="px-4 py-3 t-small" style={{ color: "var(--fg-3)" }}>
        No suggestions for this column.
      </div>
    )
  }

  return (
    <div>
      {suggestions.map((s) => {
        const isAccepted = accepted.has(s.detector_slug)
        const confPct = Math.round(s.confidence * 100)
        const confColor =
          s.confidence >= 0.8
            ? "var(--pass)"
            : s.confidence >= 0.6
            ? "var(--warn)"
            : "var(--fg-3)"
        const confBg =
          s.confidence >= 0.8
            ? "rgba(127,179,148,0.12)"
            : s.confidence >= 0.6
            ? "rgba(217,181,102,0.12)"
            : "rgba(113,113,113,0.12)"
        return (
          <div
            key={s.detector_slug}
            className="flex items-start gap-3 px-4 py-3 border-b border-line last:border-0"
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span
                  className="t-small"
                  style={{ color: "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)" }}
                >
                  {s.detector_slug}
                </span>
                <span
                  className="t-micro px-1 py-0.5"
                  style={{
                    color: confColor,
                    background: confBg,
                    fontFamily: "var(--font-jetbrains-mono)",
                  }}
                >
                  {confPct}%
                </span>
              </div>
              <p className="t-micro" style={{ color: "var(--fg-2)" }}>
                {s.rationale}
              </p>
            </div>
            <button
              onClick={() =>
                setAccepted((prev) => new Set(Array.from(prev).concat(s.detector_slug)))
              }
              disabled={isAccepted}
              className="t-micro px-2 py-1 border flex-shrink-0 transition-colors"
              style={{
                borderColor: isAccepted ? "var(--pass)" : "var(--line-3)",
                color: isAccepted ? "var(--pass)" : "var(--fg-2)",
                background: "transparent",
                cursor: isAccepted ? "default" : "pointer",
              }}
            >
              {isAccepted ? "accepted" : "accept"}
            </button>
          </div>
        )
      })}
    </div>
  )
}
