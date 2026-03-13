import React, { useCallback, useState } from 'react'
import { useUpload } from '../hooks/useUpload'

export function UploadZone({ onDocumentReady }) {
  const { state, upload, reset } = useUpload()
  const [isDragOver, setIsDragOver] = useState(false)

  const handleFile = useCallback(
    async (file) => {
      const docId = await upload(file)
      if (docId && onDocumentReady) {
        onDocumentReady(docId)
      }
    },
    [upload, onDocumentReady]
  )

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault()
      setIsDragOver(false)
      const file = e.dataTransfer.files[0]
      if (file) handleFile(file)
    },
    [handleFile]
  )

  const handleInputChange = (e) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
  }

  const stageConfig = {
    idle: { color: 'var(--border)', icon: '📁', label: '' },
    uploading: { color: 'var(--accent)', icon: '⬆️', label: `Uploading ${state.progress}%` },
    indexing: { color: 'var(--accent)', icon: '⚙️', label: 'Processing document...' },
    ready: { color: '#22c55e', icon: '✅', label: 'Ready for queries' },
    error: { color: '#ef4444', icon: '❌', label: state.error ?? 'Upload failed' },
  }

  const { icon, label } = stageConfig[state.stage] || stageConfig.idle

  return (
    <div className="space-y-3">
      {state.stage === 'idle' || state.stage === 'error' ? (
        <label
          className="flex flex-col items-center justify-center w-full h-32 rounded-xl border-2 border-dashed cursor-pointer transition-all duration-200"
          style={{
            borderColor: isDragOver ? 'var(--accent)' : 'var(--border)',
            backgroundColor: isDragOver
              ? 'color-mix(in srgb, var(--accent) 8%, transparent)'
              : 'var(--bg-secondary)',
          }}
          onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
        >
          <input
            type="file"
            className="hidden"
            accept=".pdf,.txt,.md"
            onChange={handleInputChange}
          />
          <div className="text-center">
            <p className="text-2xl mb-1">📄</p>
            <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
              Drop PDF, TXT, or MD here
            </p>
            <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
              or click to browse · max 10 MB
            </p>
          </div>
        </label>
      ) : null}

      {state.stage !== 'idle' && (
        <div
          className="rounded-xl p-3 border animate-fade-in"
          style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg-card)' }}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span>{icon}</span>
              <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                {label}
              </span>
            </div>
            {(state.stage === 'ready' || state.stage === 'error') && (
              <button
                onClick={reset}
                className="text-xs underline"
                style={{ color: 'var(--text-secondary)' }}
              >
                Upload another
              </button>
            )}
          </div>

          <div className="progress-bar-track">
            {state.stage === 'uploading' ? (
              <div
                className="progress-bar-fill"
                style={{ width: `${state.progress}%` }}
              />
            ) : state.stage === 'indexing' ? (
              <div className="progress-indeterminate">
                <div className="progress-bar-fill" />
              </div>
            ) : state.stage === 'ready' ? (
              <div
                className="progress-bar-fill"
                style={{ width: '100%', background: '#22c55e' }}
              />
            ) : state.stage === 'error' ? (
              <div
                className="progress-bar-fill"
                style={{ width: '100%', background: '#ef4444' }}
              />
            ) : null}
          </div>
        </div>
      )}
    </div>
  )
}
