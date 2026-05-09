import { create } from 'zustand'
import { conversationService, type Conversation } from '../services/api'

interface ChatState {
  conversations: Conversation[]
  currentConversationId: number | null
  isLoading: boolean
  selectedConversationIds: Set<number>
  isSelectionMode: boolean
  
  // Actions
  loadConversations: () => Promise<void>
  setCurrentConversationId: (id: number | null) => void
  deleteConversation: (id: number) => Promise<void>
  batchDeleteConversations: (ids: number[]) => Promise<void>
  refreshConversations: () => Promise<void>
  toggleConversationSelection: (id: number) => void
  selectAllConversations: () => void
  clearSelection: () => void
  setSelectionMode: (enabled: boolean) => void
}

export const useChatStore = create<ChatState>((set) => ({
  conversations: [],
  currentConversationId: null,
  isLoading: false,
  selectedConversationIds: new Set(),
  isSelectionMode: false,

  loadConversations: async () => {
    set({ isLoading: true })
    try {
      const data = await conversationService.list()
      set({ conversations: data.conversations })
    } catch (error) {
      console.error("Failed to load conversations:", error)
    } finally {
      set({ isLoading: false })
    }
  },

  setCurrentConversationId: (id) => {
    set({ currentConversationId: id })
  },

  deleteConversation: async (id) => {
    try {
      await conversationService.delete(id)
      set((state) => ({
        conversations: state.conversations.filter((c) => c.id !== id),
        currentConversationId: state.currentConversationId === id ? null : state.currentConversationId
      }))
    } catch (error) {
      console.error("Failed to delete conversation:", error)
    }
  },

  batchDeleteConversations: async (ids) => {
    try {
      await conversationService.batchDelete(ids)
      set((state) => {
        const deletedSet = new Set(ids)
        return {
          conversations: state.conversations.filter((c) => !deletedSet.has(c.id)),
          currentConversationId: deletedSet.has(state.currentConversationId!) ? null : state.currentConversationId,
          selectedConversationIds: new Set(),
          isSelectionMode: false
        }
      })
    } catch (error) {
      console.error("Failed to batch delete conversations:", error)
      throw error
    }
  },

  refreshConversations: async () => {
    const data = await conversationService.list()
    set({ conversations: data.conversations })
  },

  toggleConversationSelection: (id) => {
    set((state) => {
      const newSelection = new Set(state.selectedConversationIds)
      if (newSelection.has(id)) {
        newSelection.delete(id)
      } else {
        newSelection.add(id)
      }
      return { selectedConversationIds: newSelection }
    })
  },

  selectAllConversations: () => {
    set((state) => ({
      selectedConversationIds: new Set(state.conversations.map(c => c.id))
    }))
  },

  clearSelection: () => {
    set({ selectedConversationIds: new Set(), isSelectionMode: false })
  },

  setSelectionMode: (enabled) => {
    set({ isSelectionMode: enabled, selectedConversationIds: enabled ? new Set() : new Set() })
  }
}))
