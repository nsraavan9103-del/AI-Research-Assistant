import React from 'react'
import { CitationRenderer } from './CitationBadge'

export function ChatMessage({ role, content, citations = [], isStreaming }) {
  const isUser = role === 'user'

  return (
    <div
      className={`flex message-enter ${isUser ? 'justify-end' : 'justify-start'} mb-4`}
    >
      {!isUser && (
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center text-sm flex-shrink-0 mr-2 mt-1"
          style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-light))' }}
        >
          🤖
        </div>
      )}

      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 ${
          isUser ? 'rounded-tr-sm' : 'rounded-tl-sm'
        }`}
        style={
          isUser
            ? {
                background: 'linear-gradient(135deg, var(--accent), var(--accent-light))',
                color: '#ffffff',
              }
            : {
                backgroundColor: 'var(--bg-card)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border)',
              }
        }
      >
        <div className="text-sm leading-relaxed whitespace-pre-wrap break-words">
          {isUser ? (
            content
          ) : (
            <CitationRenderer text={content} allCitations={citations} />
          )}
          {isStreaming && (
            <span
              className="inline-block w-2 h-4 ml-0.5 align-middle animate-pulse"
              style={{ backgroundColor: 'var(--accent)' }}
            />
          )}
        </div>

        {!isUser && citations.length > 0 && !isStreaming && (
          <div
            className="mt-2 pt-2 flex flex-wrap gap-1"
            style={{ borderTop: '1px solid var(--border)' }}
          >
            <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>Sources:</span>
            {citations.map((c, i) => (
              <span
                key={i}
                className="text-xs px-1.5 py-0.5 rounded"
                style={{
                  backgroundColor: 'color-mix(in srgb, var(--accent) 12%, transparent)',
                  color: 'var(--accent)',
                }}
              >
                {c.document.slice(0, 15)}{c.document.length > 15 ? '…' : ''}, p.{c.page}
              </span>
            ))}
          </div>
        )}
      </div>

      {isUser && (
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center text-sm flex-shrink-0 ml-2 mt-1"
          style={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
        >
          👤
        </div>
      )}
    </div>
  )
}
