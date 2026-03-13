import React, { useRef, useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { useStore } from '../store/useStore'
import { useTheme } from '../contexts/ThemeContext'
import { useStreamQuery } from '../hooks/useStreamQuery'
import { UploadZone } from '../components/UploadZone'
import { ThinkingIndicator } from '../components/ThinkingIndicator'
import { ChatMessage } from '../components/ChatMessage'

export default function ChatPage() {
  const navigate = useNavigate()
  const { resolvedTheme, setTheme } = useTheme()
  const {
    accessToken,
    logout,
    documents,
    setDocuments,
    messages,
    addMessage,
    clearMessages,
    currentConversationId,
    setCurrentConversationId,
  } = useStore()

  const [question, setQuestion] = useState('')
  const [selectedDocIds, setSelectedDocIds] = useState([])
  const [useWebSearch, setUseWebSearch] = useState(false)
  const [researchMode, setResearchMode] = useState(false)
  const messagesEndRef = useRef(null)

  const { state: streamState, streamQuery } = useStreamQuery()

  useEffect(() => {
    if (!accessToken) navigate('/auth')
  }, [accessToken, navigate])

  const { refetch: refetchDocs } = useQuery({
    queryKey: ['documents'],
    queryFn: async () => {
      const { data } = await axios.get('/api/documents/', {
        headers: { Authorization: `Bearer ${accessToken}` },
      })
      setDocuments(data)
      return data
    },
    enabled: !!accessToken,
    staleTime: 30_000,
  })

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamState.currentText])

  const handleAsk = useCallback(async () => {
    const q = question.trim()
    if (!q || streamState.isStreaming) return
    setQuestion('')

    addMessage({ id: Date.now().toString(), role: 'user', content: q })

    if (researchMode) {
      try {
        const { data } = await axios.post(
          '/api/agents/research',
          {
            query: q,
            document_ids: selectedDocIds,
            conversation_id: currentConversationId || undefined,
            mode: selectedDocIds.length > 1 ? 'multi_doc' : 'research',
            use_web_search: useWebSearch,
          },
          { headers: { Authorization: `Bearer ${accessToken}` } }
        )
        addMessage({
          id: data.message_id,
          role: 'assistant',
          content: data.answer,
          citations: data.citations,
        })
        setCurrentConversationId(data.conversation_id)
      } catch (err) {
        addMessage({
          id: Date.now().toString(),
          role: 'assistant',
          content: '❌ Research agent failed. Please check that Ollama is running.',
        })
      }
    } else {
      const convId = await streamQuery(
        q,
        selectedDocIds,
        currentConversationId || undefined,
        useWebSearch
      )
      if (convId && !currentConversationId) setCurrentConversationId(convId)

      if (streamState.currentText || !streamState.error) {
        addMessage({
          id: Date.now().toString(),
          role: 'assistant',
          content: streamState.currentText || '(No response)',
          citations: streamState.citations,
        })
      }
    }
  }, [
    question,
    selectedDocIds,
    researchMode,
    useWebSearch,
    currentConversationId,
    accessToken,
    streamState,
    streamQuery,
    addMessage,
    setCurrentConversationId,
  ])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleAsk()
    }
  }

  const toggleDocSelection = (id) => {
    setSelectedDocIds((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]
    )
  }

  const handleLogout = async () => {
    try {
      await axios.post('/api/auth/logout', {}, {
        headers: { Authorization: `Bearer ${accessToken}` },
      })
    } catch { /* ignore */ }
    logout()
    navigate('/auth')
  }

  const ready = documents.filter((d) => d.status === 'ready')
  const allMessages = [...messages]

  const streamingMessage =
    streamState.isStreaming && streamState.currentText
      ? {
          id: 'streaming',
          role: 'assistant',
          content: streamState.currentText,
          citations: streamState.citations,
        }
      : null

  return (
    <div
      className="flex flex-col h-screen"
      style={{ backgroundColor: 'var(--bg-primary)' }}
    >
      <header
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{
          backgroundColor: 'var(--bg-card)',
          borderColor: 'var(--border)',
        }}
      >
        <div className="flex items-center gap-2">
          <span className="text-xl">🔬</span>
          <span className="font-bold text-base-content">AI Research Assistant</span>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 cursor-pointer">
            <span className="text-xs text-muted">Web Search</span>
            <div
              className="relative w-8 h-4 rounded-full transition-colors cursor-pointer"
              style={{ backgroundColor: useWebSearch ? 'var(--accent)' : 'var(--border)' }}
              onClick={() => setUseWebSearch((v) => !v)}
            >
              <div
                className="absolute top-0.5 w-3 h-3 rounded-full bg-white transition-all"
                style={{ left: useWebSearch ? '17px' : '2px' }}
              />
            </div>
          </label>

          <button
            className="p-1.5 rounded-lg transition-all hover:scale-110"
            style={{ backgroundColor: 'var(--bg-secondary)' }}
            onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
            title="Toggle dark mode"
          >
            {resolvedTheme === 'dark' ? '☀️' : '🌙'}
          </button>

          <button
            onClick={handleLogout}
            className="text-xs px-3 py-1.5 rounded-lg transition-all hover:opacity-80"
            style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}
          >
            Logout
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <aside
          className="w-72 flex flex-col border-r overflow-y-auto"
          style={{
            backgroundColor: 'var(--bg-secondary)',
            borderColor: 'var(--border)',
          }}
        >
          <div className="p-4 space-y-4">
            <div>
              <h3
                className="text-xs font-semibold uppercase tracking-wider mb-3"
                style={{ color: 'var(--text-secondary)' }}
              >
                Upload Document
              </h3>
              <UploadZone onDocumentReady={() => refetchDocs()} />
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <h3
                  className="text-xs font-semibold uppercase tracking-wider"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  My Documents ({ready.length})
                </h3>
                {selectedDocIds.length > 0 && (
                  <button
                    className="text-xs underline"
                    style={{ color: 'var(--accent)' }}
                    onClick={() => setSelectedDocIds([])}
                  >
                    Clear
                  </button>
                )}
              </div>

              <div className="space-y-1.5">
                {documents.length === 0 ? (
                  <p className="text-xs italic text-muted text-center py-4">
                    Upload a document to get started
                  </p>
                ) : (
                  documents.map((doc) => (
                    <DocItem
                      key={doc.id}
                      doc={doc}
                      selected={selectedDocIds.includes(doc.id)}
                      onToggle={() => toggleDocSelection(doc.id)}
                    />
                  ))
                )}
              </div>
            </div>

            <div
              className="rounded-xl p-3"
              style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border)' }}
            >
              <label className="flex items-center gap-3 cursor-pointer">
                <div
                  className="relative w-9 h-5 rounded-full transition-colors"
                  style={{ backgroundColor: researchMode ? 'var(--accent)' : 'var(--border)' }}
                  onClick={() => setResearchMode((v) => !v)}
                >
                  <div
                    className="absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all"
                    style={{ left: researchMode ? '19px' : '2px' }}
                  />
                </div>
                <div>
                  <p className="text-sm font-medium text-base-content">Research Mode</p>
                  <p className="text-xs text-muted">Multi-agent analysis</p>
                </div>
              </label>
            </div>

            <button
              onClick={() => clearMessages()}
              className="w-full py-2 rounded-xl text-sm transition-all hover:opacity-80"
              style={{
                backgroundColor: 'color-mix(in srgb, var(--accent) 12%, transparent)',
                color: 'var(--accent)',
              }}
            >
              + New Conversation
            </button>
          </div>
        </aside>

        <main className="flex flex-col flex-1 overflow-hidden">
          <div className="flex-1 overflow-y-auto px-6 py-4">
            {allMessages.length === 0 && !streamingMessage && (
              <div className="flex flex-col items-center justify-center h-full text-center gap-4">
                <div className="text-5xl">🔬</div>
                <div>
                  <h2 className="text-xl font-semibold text-base-content mb-2">
                    How can I help you?
                  </h2>
                  <p className="text-sm text-muted max-w-sm">
                    Ask a general question, search the web, or select uploaded documents to ask questions about your research.
                  </p>
                </div>
                {selectedDocIds.length === 0 && documents.length > 0 && (
                  <div
                    className="rounded-xl px-4 py-3 text-sm animate-fade-in"
                    style={{
                      backgroundColor: 'color-mix(in srgb, var(--accent) 10%, transparent)',
                      color: 'var(--accent)',
                    }}
                  >
                    💡 Select a document from the sidebar to chat with it
                  </div>
                )}
              </div>
            )}

            {allMessages.map((msg) => (
              <ChatMessage
                key={msg.id}
                role={msg.role}
                content={msg.content}
                citations={msg.citations ?? []}
              />
            ))}

            {streamingMessage && (
              <ChatMessage
                role="assistant"
                content={streamingMessage.content}
                citations={streamingMessage.citations ?? []}
                isStreaming
              />
            )}

            {streamState.isStreaming && !streamState.currentText && (
              <ThinkingIndicator
                stage={streamState.stage}
                isVisible={true}
              />
            )}

            <div ref={messagesEndRef} />
          </div>

          <div
            className="px-6 py-4 border-t"
            style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg-card)' }}
          >
            {selectedDocIds.length > 0 && (
              <div className="flex gap-1.5 mb-2 flex-wrap">
                {selectedDocIds.map((id) => {
                  const doc = documents.find((d) => d.id === id)
                  return (
                    <span
                      key={id}
                      className="text-xs px-2 py-0.5 rounded-full"
                      style={{
                        backgroundColor: 'color-mix(in srgb, var(--accent) 15%, transparent)',
                        color: 'var(--accent)',
                      }}
                    >
                      📄 {doc?.original_filename?.slice(0, 20) ?? id.slice(0, 8)}
                    </span>
                  )
                })}
              </div>
            )}
            <div className="flex gap-3">
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  researchMode
                    ? 'Ask for a deep research analysis...'
                    : selectedDocIds.length > 0
                    ? 'Ask a question about your documents... (Enter to send)'
                    : 'Ask any question or search the web... (Enter to send)'
                }
                rows={2}
                disabled={streamState.isStreaming}
                className="flex-1 rounded-xl px-4 py-3 text-sm resize-none border transition-all disabled:opacity-60"
                style={{
                  backgroundColor: 'var(--bg-secondary)',
                  borderColor: 'var(--border)',
                  color: 'var(--text-primary)',
                }}
              />
              <button
                onClick={handleAsk}
                disabled={
                  streamState.isStreaming ||
                  !question.trim()
                }
                className="px-5 py-3 rounded-xl font-semibold text-sm transition-all hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
                style={{
                  background: 'linear-gradient(135deg, var(--accent), var(--accent-light))',
                  color: '#ffffff',
                }}
              >
                {streamState.isStreaming ? '⏳' : researchMode ? '🔍 Research' : '→ Ask'}
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

function DocItem({ doc, selected, onToggle }) {
  const statusColor = {
    ready: '#22c55e',
    pending: 'var(--text-secondary)',
    indexing: 'var(--accent)',
    failed: '#ef4444',
  }[doc.status] ?? 'var(--text-secondary)'

  const statusIcon = { ready: '✅', pending: '⏳', indexing: '⚙️', failed: '❌' }[doc.status] ?? '❓'

  return (
    <button
      onClick={onToggle}
      disabled={doc.status !== 'ready'}
      className="w-full text-left px-3 py-2 rounded-xl text-xs transition-all"
      style={{
        backgroundColor: selected
          ? 'color-mix(in srgb, var(--accent) 15%, transparent)'
          : 'var(--bg-card)',
        borderLeft: selected ? '3px solid var(--accent)' : '3px solid transparent',
        opacity: doc.status !== 'ready' ? 0.6 : 1,
      }}
    >
      <div className="flex items-center justify-between">
        <span
          className="truncate font-medium"
          style={{ color: 'var(--text-primary)', maxWidth: '160px' }}
        >
          {doc.original_filename}
        </span>
        <span title={doc.status}>{statusIcon}</span>
      </div>
      <div className="flex items-center justify-between mt-0.5">
        <span style={{ color: statusColor }}>
          {doc.status === 'ready'
            ? `${doc.total_chunks} chunks`
            : doc.status === 'indexing'
            ? 'Processing...'
            : doc.status}
        </span>
        <span style={{ color: 'var(--text-secondary)' }}>
          {(doc.file_size_bytes / 1024).toFixed(0)} KB
        </span>
      </div>
    </button>
  )
}
