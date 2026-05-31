"use client"

import { useState, useEffect } from "react"

interface Suggestion {
  detector_slug: string
  params: Record<string, unknown>
  rationale: string
  confidence: number
}

interface DetectorDef {
  group: string
  slug: string
  label: string
  params: Record<string, unknown>
}

interface ExistingCheck {
  id: string
  detector_slug: string
  params: Record<string, unknown>
}

const CONF_COLOR = (c: number) =>
  c >= 0.8 ? "var(--pass)" : c >= 0.6 ? "var(--warn)" : "var(--fg-3)"
const CONF_BG = (c: number) =>
  c >= 0.8 ? "rgba(127,179,148,0.12)" : c >= 0.6 ? "rgba(217,181,102,0.12)" : "rgba(113,113,113,0.12)"

export function SuggestPanel({
  datasetId,
  column,
  existingChecks,
  onCheckAdded,
  onCheckDeleted,
}: {
  datasetId: string
  column: string
  existingChecks: ExistingCheck[]
  onCheckAdded?: (check: ExistingCheck) => void
  onCheckDeleted?: (checkId: string) => void
}) {
  const [tab, setTab] = useState<"suggested" | "all">("suggested")
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [allDetectors, setAllDetectors] = useState<DetectorDef[]>([])
  const [loadingSugg, setLoadingSugg] = useState(true)
  const [loadingAll, setLoadingAll] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [accepted, setAccepted] = useState<Set<string>>(new Set())
  const [editing, setEditing] = useState<string | null>(null)
  const [editParams, setEditParams] = useState("")
  const [addSlug, setAddSlug] = useState("")
  const [adding, setAdding] = useState(false)

  useEffect(() => {
    setLoadingSugg(true)
    fetch(`/api/v1/datasets/${encodeURIComponent(datasetId)}/columns/${encodeURIComponent(column)}/suggest`)
      .then((r) => (r.ok ? r.json() : []))
      .then(setSuggestions)
      .catch(() => setSuggestions([]))
      .finally(() => setLoadingSugg(false))
  }, [datasetId, column])

  useEffect(() => {
    if (tab !== "all" || allDetectors.length > 0) return
    setLoadingAll(true)
    fetch("/api/v1/detectors")
      .then((r) => (r.ok ? r.json() : []))
      .then(setAllDetectors)
      .catch(() => setAllDetectors([]))
      .finally(() => setLoadingAll(false))
  }, [tab, allDetectors.length])

  async function acceptSuggestion(s: Suggestion) {
    const resp = await fetch(
      `/api/v1/datasets/${encodeURIComponent(datasetId)}/columns/${encodeURIComponent(column)}/checks`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ detector_slug: s.detector_slug, params: s.params, rationale: s.rationale }),
      }
    )
    if (resp.ok) {
      const created = await resp.json()
      setAccepted((prev) => new Set(Array.from(prev).concat(s.detector_slug)))
      onCheckAdded?.(created)
    }
  }

  async function addCustom(slug: string, params: Record<string, unknown> = {}) {
    setAdding(true)
    const resp = await fetch(
      `/api/v1/datasets/${encodeURIComponent(datasetId)}/columns/${encodeURIComponent(column)}/checks`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ detector_slug: slug, params }),
      }
    )
    if (resp.ok) {
      const created = await resp.json()
      setAccepted((prev) => new Set(Array.from(prev).concat(slug)))
      onCheckAdded?.(created)
    }
    setAdding(false)
    setEditing(null)
  }

  async function deleteCheck(id: string, slug: string) {
    const resp = await fetch(`/api/v1/checks/${id}`, { method: "DELETE" })
    if (resp.ok) {
      setAccepted((prev) => { const s = new Set(prev); s.delete(slug); return s })
      onCheckDeleted?.(id)
    }
  }

  const existingSlugs = new Set(existingChecks.map((c) => c.detector_slug))

  const filteredDetectors = allDetectors.filter(
    (d) =>
      !searchQuery ||
      d.slug.includes(searchQuery.toLowerCase()) ||
      d.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.group.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const grouped: Record<string, DetectorDef[]> = {}
  filteredDetectors.forEach((d) => {
    if (!grouped[d.group]) grouped[d.group] = []
    grouped[d.group].push(d)
  })

  return (
    <div>
      {/* Tabs */}
      <div className="flex border-b border-line">
        {(["suggested", "all"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className="px-4 py-2 t-micro transition-colors"
            style={{
              color: tab === t ? "var(--accent)" : "var(--fg-3)",
              borderBottom: tab === t ? "1px solid var(--accent)" : "1px solid transparent",
              marginBottom: -1,
              background: "transparent",
              letterSpacing: "0.06em",
              textTransform: "uppercase",
            }}
          >
            {t === "suggested" ? "Suggested" : "All Detectors"}
          </button>
        ))}
      </div>

      {/* Suggested tab */}
      {tab === "suggested" && (
        <div>
          {loadingSugg ? (
            <div className="px-4 py-3 t-small" style={{ color: "var(--fg-3)" }}>
              Analyzing column...
            </div>
          ) : suggestions.length === 0 ? (
            <div className="px-4 py-3 t-small" style={{ color: "var(--fg-3)" }}>
              No suggestions for this column.
            </div>
          ) : (
            suggestions.map((s) => {
              const isAccepted = accepted.has(s.detector_slug) || existingSlugs.has(s.detector_slug)
              const matchingCheck = existingChecks.find((c) => c.detector_slug === s.detector_slug)
              return (
                <div
                  key={s.detector_slug}
                  className="flex items-start gap-3 px-4 py-3 border-b border-line last:border-0"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="t-small" style={{ color: "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)" }}>
                        {s.detector_slug}
                      </span>
                      <span
                        className="t-micro px-1 py-0.5"
                        style={{ color: CONF_COLOR(s.confidence), background: CONF_BG(s.confidence), fontFamily: "var(--font-jetbrains-mono)" }}
                      >
                        {Math.round(s.confidence * 100)}%
                      </span>
                    </div>
                    <p className="t-micro" style={{ color: "var(--fg-2)" }}>{s.rationale}</p>
                    {editing === s.detector_slug && (
                      <div className="mt-2 flex gap-2 items-center">
                        <input
                          value={editParams}
                          onChange={(e) => setEditParams(e.target.value)}
                          placeholder='{"threshold": 3.5}'
                          className="flex-1 border border-line px-2 py-1 t-micro bg-transparent outline-none"
                          style={{ color: "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)" }}
                        />
                        <button
                          onClick={() => {
                            try { addCustom(s.detector_slug, editParams ? JSON.parse(editParams) : s.params) }
                            catch { addCustom(s.detector_slug, s.params) }
                          }}
                          className="t-micro px-2 py-1 border border-accent"
                          style={{ color: "var(--accent)", background: "var(--accent-bg)", cursor: "pointer" }}
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setEditing(null)}
                          className="t-micro px-2 py-1 border border-line"
                          style={{ color: "var(--fg-2)", cursor: "pointer" }}
                        >
                          Cancel
                        </button>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    {!isAccepted && (
                      <button
                        onClick={() => { setEditing(s.detector_slug); setEditParams(JSON.stringify(s.params, null, 2)) }}
                        className="t-micro px-2 py-1 border border-line transition-colors hover:border-accent"
                        style={{ color: "var(--fg-2)", cursor: "pointer" }}
                      >
                        Edit
                      </button>
                    )}
                    <button
                      onClick={() => !isAccepted && acceptSuggestion(s)}
                      disabled={isAccepted}
                      className="t-micro px-2 py-1 border flex-shrink-0"
                      style={{
                        borderColor: isAccepted ? "var(--pass)" : "var(--line)",
                        color: isAccepted ? "var(--pass)" : "var(--fg-0)",
                        background: isAccepted ? "transparent" : "var(--bg-2)",
                        cursor: isAccepted ? "default" : "pointer",
                      }}
                    >
                      {isAccepted ? "added" : "Accept"}
                    </button>
                    {isAccepted && matchingCheck && (
                      <button
                        onClick={() => deleteCheck(matchingCheck.id, s.detector_slug)}
                        className="t-micro px-2 py-1 border border-line transition-colors hover:border-fail"
                        style={{ color: "var(--fg-3)", cursor: "pointer" }}
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </div>
              )
            })
          )}
        </div>
      )}

      {/* All detectors tab */}
      {tab === "all" && (
        <div>
          <div className="px-4 py-2 border-b border-line">
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search detectors..."
              className="w-full border border-line px-2 py-1 t-small bg-transparent outline-none"
              style={{ color: "var(--fg-0)" }}
            />
          </div>
          {loadingAll ? (
            <div className="px-4 py-3 t-small" style={{ color: "var(--fg-3)" }}>Loading...</div>
          ) : (
            Object.entries(grouped).map(([group, dets]) => (
              <div key={group}>
                <div
                  className="px-4 py-1.5 t-micro"
                  style={{
                    color: "var(--fg-3)", background: "var(--bg-0)",
                    letterSpacing: "0.10em", textTransform: "uppercase",
                    borderBottom: "1px solid var(--line)",
                  }}
                >
                  {group}
                </div>
                {dets.map((d) => {
                  const isAdded = existingSlugs.has(d.slug)
                  const matchingCheck = existingChecks.find((c) => c.detector_slug === d.slug)
                  return (
                    <div
                      key={d.slug}
                      className="flex items-center justify-between px-4 py-2 border-b border-line last:border-0"
                    >
                      <div>
                        <span className="t-small" style={{ color: "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)" }}>
                          {d.slug}
                        </span>
                        {d.label && (
                          <span className="t-micro ml-2" style={{ color: "var(--fg-3)" }}>{d.label}</span>
                        )}
                      </div>
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => !isAdded && addCustom(d.slug, d.params)}
                          disabled={isAdded || adding}
                          className="t-micro px-2 py-1 border flex-shrink-0"
                          style={{
                            borderColor: isAdded ? "var(--pass)" : "var(--line)",
                            color: isAdded ? "var(--pass)" : "var(--fg-1)",
                            background: "transparent",
                            cursor: isAdded || adding ? "default" : "pointer",
                            opacity: adding ? 0.5 : 1,
                          }}
                        >
                          {isAdded ? "added" : "+ Add"}
                        </button>
                        {isAdded && matchingCheck && (
                          <button
                            onClick={() => deleteCheck(matchingCheck.id, d.slug)}
                            className="t-micro px-2 py-1 border border-line transition-colors hover:border-fail"
                            style={{ color: "var(--fg-3)", cursor: "pointer" }}
                          >
                            Delete
                          </button>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            ))
          )}
          {/* Custom entry */}
          <div className="px-4 py-3 border-t border-line flex gap-2 items-center">
            <input
              value={addSlug}
              onChange={(e) => setAddSlug(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && addSlug.trim()) addCustom(addSlug.trim()) }}
              placeholder="Custom detector slug..."
              className="flex-1 border border-line px-2 py-1 t-small bg-transparent outline-none"
              style={{ color: "var(--fg-0)", fontFamily: "var(--font-jetbrains-mono)" }}
            />
            <button
              onClick={() => addSlug.trim() && addCustom(addSlug.trim())}
              disabled={!addSlug.trim() || adding}
              className="t-small px-3 py-1 border border-line hover:border-accent transition-colors disabled:opacity-40"
              style={{ color: "var(--fg-1)", cursor: "pointer" }}
            >
              Add
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
