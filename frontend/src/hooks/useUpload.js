import { useState, useRef } from 'react'
import axios from 'axios'
import { useStore } from '../store/useStore'

const initialState = {
  progress: 0,
  indexingStage: '',
  stage: 'idle',
  documentId: null,
  error: null,
}

export function useUpload() {
  const [state, setState] = useState(initialState)
  const eventSourceRef = useRef(null)
  const { accessToken, addDocument, updateDocument } = useStore()

  const upload = async (file) => {
    setState({ ...initialState, stage: 'uploading' })

    const formData = new FormData()
    formData.append('file', file)

    try {
      const { data } = await axios.post('/api/documents/upload', formData, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (e) => {
          const progress = Math.round(((e.loaded ?? 0) / (e.total ?? 1)) * 100)
          setState((s) => ({ ...s, progress }))
        },
      })

      const docId = data.document_id

      addDocument({
        id: docId,
        filename: file.name,
        original_filename: file.name,
        status: data.status === 'duplicate' ? 'ready' : 'pending',
        total_chunks: 0,
        file_size_bytes: file.size,
        created_at: new Date().toISOString(),
      })

      if (data.status === 'duplicate') {
        setState((s) => ({ ...s, stage: 'ready', documentId: docId }))
        return docId
      }

      setState((s) => ({ ...s, stage: 'indexing', documentId: docId }))
      subscribeToProgress(docId)
      return docId
    } catch (err) {
      const msg =
        axios.isAxiosError(err)
          ? (err.response?.data?.detail ?? err.message)
          : 'Upload failed'
      setState((s) => ({ ...s, stage: 'error', error: msg }))
      return null
    }
  }

  const subscribeToProgress = (docId) => {
    eventSourceRef.current?.close()

    const es = new EventSource(
      `/api/documents/${docId}/progress?token=${encodeURIComponent(
        accessToken ?? ''
      )}`
    )
    eventSourceRef.current = es

    es.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        const status = payload.status

        updateDocument(docId, {
          status: status,
          total_chunks: payload.total_chunks ?? 0,
        })

        setState((s) => ({
          ...s,
          indexingStage: status,
          stage:
            status === 'ready'
              ? 'ready'
              : status === 'failed'
              ? 'error'
              : 'indexing',
          error: status === 'failed' ? 'Indexing failed' : null,
        }))

        if (status === 'ready' || status === 'failed') {
          es.close()
        }
      } catch {
        // Ignore parse errors
      }
    }

    es.onerror = () => {
      setState((s) => ({
        ...s,
        stage: 'error',
        error: 'Lost connection during indexing',
      }))
      es.close()
    }
  }

  const reset = () => {
    eventSourceRef.current?.close()
    setState(initialState)
  }

  return { state, upload, reset }
}
