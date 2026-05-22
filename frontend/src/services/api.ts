import axios from 'axios'
import { useAuthStore } from '../store/useAuthStore'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add token
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
    }
    return Promise.reject(error)
  }
)

export interface User {
  id: number
  username: string
  email: string
  full_name?: string
  is_active: boolean
  is_superuser: boolean
  last_login?: string
  created_at: string
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface ChatMessage {
  id?: number
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at?: string
  metadata?: any
}

export interface Conversation {
  id: number
  title: string | null
  summary?: string
  created_at: string
  updated_at: string
  message_count: number
}

export interface ChatResponse {
  conversation_id: number
  message_id: number
  answer: string
  sources: Source[]
  reasoning_steps?: any[]
  execution_time?: number
}

export interface Source {
  content: string
  source: string
  relevance_score?: number
  url?: string
  type?: 'document' | 'web'
  source_type?: string
  metadata?: Record<string, any>
  images?: Array<{
    base64: string
    page?: number
    width?: number
    height?: number
  }>
}

export interface Document {
  source: string
  author?: string
  date?: string
  chunks: number
  collection?: string
  file_type?: string
}

export interface Collection {
  name: string
  count: number
  error?: string
}

export interface FileTypeStat {
  type: string
  count: number
  label: string
  icon: string
  extensions: string[]
}

export const authService = {
  async login(data: any) {
    const response = await api.post<AuthResponse>('/auth/login', data)
    return response.data
  },

  async register(data: any) {
    const response = await api.post<User>('/auth/register', data)
    return response.data
  },

  async getCurrentUser() {
    const response = await api.get<User>('/auth/me')
    return response.data
  },

  async changePassword(data: any) {
    const response = await api.post('/auth/change-password', data)
    return response.data
  },

  async sendVerificationCode(email: string) {
    const response = await api.post('/auth/send-verification-code', { email })
    return response.data
  },
}

export interface LLMConfig {
  provider: string
  base_url: string
  api_key: string
  model_name: string
  temperature: number
  max_tokens: number
  source?: string  // "saved" | "tested_fallback" | "default"
}

export interface LLMPreset {
  name: string
  base_url: string
  model_name: string
}

export interface TestConnectionResult {
  success: boolean
  message: string
  hint?: string
  elapsed_ms?: number
  method?: string
  available_models?: string[]
  requested_model_available?: boolean
}

export const settingsService = {
  async getLLMConfig() {
    const response = await api.get<LLMConfig>('/settings/llm-config')
    return response.data
  },

  async updateLLMConfig(data: LLMConfig) {
    const response = await api.put<LLMConfig>('/settings/llm-config', data)
    return response.data
  },

  async testLLMConnection(data: LLMConfig) {
    const response = await api.post<TestConnectionResult>('/settings/llm-config/test', data)
    return response.data
  },

  async getLLMPresets() {
    const response = await api.get<{ presets: LLMPreset[] }>('/settings/llm-presets')
    return response.data
  },

  async resetLLMConfig() {
    const response = await api.put<LLMConfig>('/settings/llm-config/reset')
    return response.data
  },

  async getTestedModels() {
    const response = await api.get<{ models: (LLMConfig & { tested_at: number; connected: boolean })[] }>('/settings/tested-models')
    return response.data
  },

  async saveTestedModel(data: LLMConfig) {
    const response = await api.post<{ models: any[] }>('/settings/tested-models', data)
    return response.data
  },

  async removeTestedModel(providerName: string) {
    const response = await api.delete(`/settings/tested-models/${encodeURIComponent(providerName)}`)
    return response.data
  },
}

export const conversationService = {
  async list(limit = 20, offset = 0) {
    const response = await api.get<{ total: number, conversations: Conversation[] }>(`/chat/conversations?limit=${limit}&offset=${offset}`)
    return response.data
  },
  
  async create(title?: string) {
    const response = await api.post<Conversation>('/chat/conversations', { title })
    return response.data
  },
  
  async get(id: number) {
    const response = await api.get<Conversation>(`/chat/conversations/${id}`)
    return response.data
  },
  
  async delete(id: number) {
    const response = await api.delete(`/chat/conversations/${id}`)
    return response.data
  },
  
  async batchDelete(ids: number[]) {
    const response = await api.post('/chat/conversations/batch-delete', ids)
    return response.data
  },
  
  async getMessages(id: number) {
    const response = await api.get<{ messages: ChatMessage[] }>(`/chat/conversations/${id}/messages`)
    return response.data
  }
}

export type ChatMode = 'chat' | 'rag' | 'agent'

export interface StreamEvent {
  type: 'info' | 'content' | 'sources' | 'status' | 'done' | 'error'
  content?: string
  conversation_id?: number
  sources?: Source[]
  message?: string
  execution_time?: number
}

export const chatService = {
  async send(data: { 
    message: string
    conversation_id?: number | null
    mode?: ChatMode
    top_k?: number
    min_relevance_score?: number
    return_sources?: boolean
  }) {
    const response = await api.post<ChatResponse>('/chat/send', data)
    return response.data
  },

  /**
   * 流式发送消息，返回AsyncGenerator
   */
  async *stream(
    data: {
      message: string
      conversation_id?: number | null
      mode?: ChatMode
      top_k?: number
      min_relevance_score?: number
      web_search?: boolean
      image_base64?: string | null
      model_name?: string | null
    },
    onEvent?: (event: StreamEvent) => void
  ): AsyncGenerator<StreamEvent, void, unknown> {
    const token = useAuthStore.getState().token
    
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
      },
      body: JSON.stringify(data)
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('No response body')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event: StreamEvent = JSON.parse(line.slice(6))
            if (onEvent) onEvent(event)
            yield event
          } catch (e) {
            console.error('Failed to parse SSE event:', line)
          }
        }
      }
    }
  },

  async quickQuery(data: {
    message: string
    mode?: ChatMode
    top_k?: number
  }) {
    const response = await api.post<any>('/chat/quick-query', data)
    return response.data
  },

  async generateFollowUp(question: string, answer: string, language?: 'en' | 'zh') {
    const response = await api.post<{ questions: string[] }>('/chat/follow-up', {
      question,
      answer,
      ...(language ? { language } : {}),
    })
    return response.data
  },

  async search(query: string) {
    const response = await api.post<ChatResponse>('/rag/query', {
      query,
      top_k: 5
    })
    return response.data
  },
  
  async getDocuments(fileType?: string) {
    const params = fileType ? `?file_type=${encodeURIComponent(fileType)}` : ''
    const response = await api.get<{ total: number, documents: Document[] }>(`/documents/list${params}`)
    return response.data
  },

  async getFileTypeStats() {
    const response = await api.get<{ total: number, stats: FileTypeStat[] }>('/documents/file-types')
    return response.data
  },

  async getDocumentContent(source: string, collection?: string) {
    const params = collection ? `?collection=${encodeURIComponent(collection)}` : ''
    const response = await api.get<{
      source: string
      content: string
      chunks: Array<{ chunk_id: number, content: string, metadata: any }>
      chunk_count: number
      metadata: any
      images?: Array<{ base64: string, width: number, height: number, page: number, index: number }>
      image_count?: number
    }>(`/documents/content/${encodeURIComponent(source)}${params}`)
    return response.data
  },

  async updateDocumentContent(source: string, content: string, collection?: string) {
    const response = await api.put(`/documents/content/${encodeURIComponent(source)}`, {
      content,
      collection
    })
    return response.data
  },

  async uploadDocument(file: File, collection?: string) {
    const formData = new FormData()
    formData.append('file', file)
    if (collection) {
      formData.append('collection', collection)
    }

    const token = useAuthStore.getState().token
    const response = await fetch('/api/documents/upload-file', {
      method: 'POST',
      headers: {
        'Authorization': token ? `Bearer ${token}` : ''
      },
      body: formData
    })

    if (!response.ok) {
      const error = await response.json()
      throw { response: { data: error } }
    }

    return response.json()
  },

  async uploadDocumentsBatch(files: File[], collection?: string) {
    const formData = new FormData()
    for (const file of files) {
      formData.append('files', file)
    }
    if (collection) {
      formData.append('collection', collection)
    }

    const token = useAuthStore.getState().token
    const response = await fetch('/api/documents/upload-batch', {
      method: 'POST',
      headers: {
        'Authorization': token ? `Bearer ${token}` : ''
      },
      body: formData
    })

    if (!response.ok) {
      const error = await response.json()
      throw { response: { data: error } }
    }

    return response.json()
  },

  async deleteDocumentBySource(source: string, collection?: string) {
    const params = collection ? `?collection=${encodeURIComponent(collection)}` : ''
    const response = await api.delete(`/documents/by-source/${encodeURIComponent(source)}${params}`)
    return response.data
  },

  async rebuildIndex() {
    const response = await api.post('/documents/rebuild_index', { rebuild: true })
    return response.data
  },

  async getCollections() {
    const response = await api.get<{ total: number, collections: Collection[] }>('/documents/collections')
    return response.data
  },

  async deleteCollection(name: string) {
    const response = await api.delete(`/documents/collections/${encodeURIComponent(name)}`)
    return response.data
  },

  async createCollection(name: string) {
    const response = await api.post('/documents/collections', { name })
    return response.data
  },

  async renameCollection(oldName: string, newName: string) {
    const response = await api.put(`/documents/collections/${encodeURIComponent(oldName)}`, { new_name: newName })
    return response.data
  }
}

export default api
