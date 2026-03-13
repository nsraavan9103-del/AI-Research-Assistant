import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useStore = create(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      setTokens: (access, refresh) =>
        set({ accessToken: access, refreshToken: refresh }),
      setUser: (user) => set({ user }),
      logout: () =>
        set({
          accessToken: null,
          refreshToken: null,
          user: null,
          documents: [],
          messages: [],
          currentConversationId: null,
        }),

      documents: [],
      setDocuments: (docs) => set({ documents: docs }),
      addDocument: (doc) =>
        set((state) => ({ documents: [doc, ...state.documents] })),
      updateDocument: (id, updates) =>
        set((state) => ({
          documents: state.documents.map((d) =>
            d.id === id ? { ...d, ...updates } : d
          ),
        })),

      currentConversationId: null,
      setCurrentConversationId: (id) => set({ currentConversationId: id }),
      messages: [],
      setMessages: (msgs) => set({ messages: msgs }),
      addMessage: (msg) =>
        set((state) => ({ messages: [...state.messages, msg] })),
      clearMessages: () => set({ messages: [], currentConversationId: null }),
    }),
    {
      name: 'ai-research-store',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
        currentConversationId: state.currentConversationId,
      }),
    }
  )
)
