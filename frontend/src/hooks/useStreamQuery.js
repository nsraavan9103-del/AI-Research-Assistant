import { useState, useRef, useCallback } from 'react'
import { useStore } from '../store/useStore'

export function useStreamQuery() {
  const [state, setState] = useState({
    isStreaming: false,
    currentText: '',
    stage: '',
    citations: [],
    error: null,
  })
  const abortRef = useRef(null)
  const { accessToken } = useStore()

  const streamQuery = useCallback(
    async (
      question,
      documentIds,
      conversationId,
      useWebSearch = false
    ) => {
      abortRef.current?.abort()
      abortRef.current = new AbortController()

      setState({
        isStreaming: true,
        currentText: '',
        stage: 'Searching documents...',
        citations: [],
        error: null,
      })

      try {
        const response = await fetch('/api/query/stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${accessToken}`,
          },
          body: JSON.stringify({
            question,
            document_ids: documentIds,
            conversation_id: conversationId,
            use_web_search: useWebSearch,
          }),
          signal: abortRef.current.signal,
        })

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let conversationIdOut = null

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const raw = decoder.decode(value, { stream: true })
          const lines = raw.split('\n')

          for (const line of lines) {
            if (!line.startsWith('data:')) continue
            const jsonStr = line.slice(5).trim()
            if (!jsonStr) continue

            try {
              const payload = JSON.parse(jsonStr)

              if (payload.stage) {
                setState((s) => ({ ...s, stage: payload.stage }))
              } else if (payload.token != null) {
                setState((s) => ({
                  ...s,
                  currentText: s.currentText + payload.token,
                }))
              } else if (payload.citations) {
                setState((s) => ({
                  ...s,
                  citations: payload.citations,
                }))
              } else if (payload.done) {
                conversationIdOut = payload.conversation_id ?? null
              } else if (payload.error) {
                throw new Error(payload.error)
              }
            } catch {
              // Skip
            }
          }
        }

        setState((s) => ({ ...s, isStreaming: false, stage: '' }))
        return { conversationId: conversationIdOut, fullText: state.currentText }
      } catch (err) {
        if (err.name === 'AbortError') {
          setState((s) => ({ ...s, isStreaming: false }))
          return null
        }
        const msg = err instanceof Error ? err.message : 'Stream failed'
        setState((s) => ({ ...s, isStreaming: false, error: msg }))
        return { conversationId: null, fullText: '' }
      }
    },
    [accessToken]
  )

  const abort = useCallback(() => {
    abortRef.current?.abort()
    setState((s) => ({ ...s, isStreaming: false }))
  }, [])

  return { state, streamQuery, abort }
}
