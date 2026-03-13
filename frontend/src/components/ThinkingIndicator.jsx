import React, { useEffect, useState } from 'react'

const THINKING_STAGES = [
  { label: 'Searching documents...', icon: '🔍' },
  { label: 'Retrieving relevant chunks...', icon: '📄' },
  { label: 'Reranking results...', icon: '⚡' },
  { label: 'Synthesizing answer...', icon: '🧠' },
]

export function ThinkingIndicator({ stage, isVisible }) {
  const [currentStageIndex, setCurrentStageIndex] = useState(0)

  useEffect(() => {
    if (!isVisible) {
      setCurrentStageIndex(0)
      return
    }
    const interval = setInterval(() => {
      setCurrentStageIndex((i) => Math.min(i + 1, THINKING_STAGES.length - 1))
    }, 2000)
    return () => clearInterval(interval)
  }, [isVisible])

  if (!isVisible) return null

  const currentStage = stage || THINKING_STAGES[currentStageIndex].label
  const icon = THINKING_STAGES[currentStageIndex].icon

  return (
    <div className="flex items-center gap-3 px-4 py-3 rounded-xl animate-fade-in"
      style={{ backgroundColor: 'var(--bg-secondary)' }}>
      <div className="flex gap-1">
        <div className="thinking-dot" />
        <div className="thinking-dot" />
        <div className="thinking-dot" />
      </div>

      <div className="flex items-center gap-2">
        <span className="text-sm">{icon}</span>
        <span className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
          {currentStage}
        </span>
      </div>

      <div className="flex-1 progress-bar-track ml-2">
        <div className="progress-indeterminate" style={{ display: 'contents' }}>
          <div className="progress-bar-fill" />
        </div>
      </div>
    </div>
  )
}
