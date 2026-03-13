import React, { useState, useRef, useEffect } from 'react'

export function CitationBadge({ citation, index }) {
  const [open, setOpen] = useState(false)
  const popoverRef = useRef(null)

  useEffect(() => {
    const handler = (e) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    if (open) document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const shortName = citation.document.length > 20
    ? citation.document.slice(0, 18) + '…'
    : citation.document

  return (
    <span className="relative inline-block" ref={popoverRef}>
      <button
        className="citation-badge"
        onClick={() => setOpen((o) => !o)}
        title={`${citation.document}, p.${citation.page}`}
      >
        [{index + 1}]
      </button>

      {open && (
        <div
          className="absolute z-50 bottom-full mb-2 left-0 w-72 rounded-xl border border-base bg-card shadow-card-lg animate-fade-in p-3"
          style={{
            backgroundColor: 'var(--bg-card)',
            borderColor: 'var(--border)',
            boxShadow: 'var(--shadow-lg)',
          }}
        >
          <div className="flex items-start gap-2 mb-2">
            <span className="text-lg">📄</span>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-base-content truncate">
                {shortName}
              </p>
              <p className="text-xs text-muted">Page {citation.page}</p>
            </div>
          </div>

          <div className="h-px bg-border mb-2" style={{ backgroundColor: 'var(--border)' }} />

          {citation.snippet ? (
            <p className="text-xs text-muted leading-relaxed line-clamp-4">
              "{citation.snippet}"
            </p>
          ) : (
            <p className="text-xs text-muted italic">
              Source: {citation.document}, Page {citation.page}
            </p>
          )}
        </div>
      )}
    </span>
  )
}

export function CitationRenderer({ text, allCitations }) {
  const parts = text.split(/(\[Source:[^\]]+\])/g)

  return (
    <span>
      {parts.map((part, i) => {
        const match = part.match(/\[Source:\s*([^,\]]+),\s*p\.(\d+)\]/)
        if (match) {
          const docName = match[1].trim()
          const page = parseInt(match[2])
          const citIdx = allCitations.findIndex(
            (c) => c.document === docName && c.page === page
          )
          const citation = citIdx >= 0
            ? allCitations[citIdx]
            : { document: docName, page }
          return (
            <CitationBadge
              key={i}
              citation={citation}
              index={citIdx >= 0 ? citIdx : i}
            />
          )
        }
        return <span key={i}>{part}</span>
      })}
    </span>
  )
}
