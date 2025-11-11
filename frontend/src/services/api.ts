import axios, { AxiosInstance, AxiosRequestConfig } from 'axios'
import Cookies from 'js-cookie'
import toast from 'react-hot-toast'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = Cookies.get('access_token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config

        // Handle 401 Unauthorized
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true

          try {
            // Try to refresh token
            await this.refreshToken()
            const newToken = Cookies.get('access_token')
            if (newToken) {
              originalRequest.headers.Authorization = `Bearer ${newToken}`
              return this.client(originalRequest)
            }
          } catch (refreshError) {
            // Refresh failed, redirect to login
            this.logout()
            window.location.href = '/login'
            return Promise.reject(refreshError)
          }
        }

        // Handle other errors
        const errorMessage = error.response?.data?.error?.message || error.message || 'An error occurred'

        if (error.response?.status >= 500) {
          toast.error('Server error. Please try again later.')
        } else if (error.response?.status === 429) {
          toast.error('Too many requests. Please wait a moment.')
        } else if (!originalRequest._skipErrorHandling) {
          toast.error(errorMessage)
        }

        return Promise.reject(error)
      }
    )
  }

  // Authentication methods
  async login(email: string, password: string) {
    const formData = new FormData()
    formData.append('username', email)
    formData.append('password', password)

    const response = await this.client.post('/api/v1/auth/token', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })

    const { access_token, expires_in } = response.data
    Cookies.set('access_token', access_token, {
      expires: expires_in / (60 * 60 * 24), // Convert seconds to days
      secure: import.meta.env.PROD,
      sameSite: 'strict',
    })

    return response.data
  }

  async register(userData: {
    email: string
    password: string
    first_name?: string
    last_name?: string
  }) {
    const response = await this.client.post('/api/v1/auth/register', userData)
    return response.data
  }

  async refreshToken() {
    const response = await this.client.post('/api/v1/auth/refresh')
    const { access_token } = response.data

    Cookies.set('access_token', access_token, {
      expires: 30 / (60 * 60 * 24), // 30 minutes to days
      secure: import.meta.env.PROD,
      sameSite: 'strict',
    })

    return response.data
  }

  logout() {
    Cookies.remove('access_token')
    this.client.post('/api/v1/auth/logout').catch(() => {})
  }

  async getCurrentUser() {
    const response = await this.client.get('/api/v1/auth/me')
    return response.data
  }

  async verifyToken() {
    const response = await this.client.get('/api/v1/auth/verify')
    return response.data
  }

  // Chat methods
  async askQuestion(query: {
    query: string
    session_id?: string
    retrieval_config?: {
      k: number
      rerank: boolean
      filters?: Record<string, any>
      threshold?: number
    }
  }) {
    const response = await this.client.post('/api/v1/chat/ask', query)
    return response.data
  }

  async createSession(sessionData?: {
    title?: string
    description?: string
  }) {
    const response = await this.client.post('/api/v1/chat/sessions', sessionData || {})
    return response.data
  }

  async getSessions(params: {
    page?: number
    page_size?: number
  } = {}) {
    const response = await this.client.get('/api/v1/chat/sessions', { params })
    return response.data
  }

  async getSession(sessionId: string) {
    const response = await this.client.get(`/api/v1/chat/sessions/${sessionId}`)
    return response.data
  }

  async updateSession(sessionId: string, updates: {
    title?: string
    description?: string
    is_active?: boolean
  }) {
    const response = await this.client.put(`/api/v1/chat/sessions/${sessionId}`, updates)
    return response.data
  }

  async deleteSession(sessionId: string) {
    const response = await this.client.delete(`/api/v1/chat/sessions/${sessionId}`)
    return response.data
  }

  async getSessionHistory(sessionId: string, params: {
    page?: number
    page_size?: number
  } = {}) {
    const response = await this.client.get(`/api/v1/chat/sessions/${sessionId}/history`, { params })
    return response.data
  }

  async updateMessageFeedback(messageId: string, feedback: {
    feedback?: 'helpful' | 'not_helpful' | 'inappropriate'
    feedback_comment?: string
  }) {
    const response = await this.client.put(`/api/v1/chat/messages/${messageId}/feedback`, feedback)
    return response.data
  }

  async getChatStats() {
    const response = await this.client.get('/api/v1/chat/stats')
    return response.data
  }

  // Document methods
  async uploadDocument(file: File, metadata: {
    title?: string
    description?: string
    access_level?: string
    tags?: string
  }) {
    const formData = new FormData()
    formData.append('file', file)

    if (metadata.title) formData.append('title', metadata.title)
    if (metadata.description) formData.append('description', metadata.description)
    if (metadata.access_level) formData.append('access_level', metadata.access_level)
    if (metadata.tags) formData.append('tags', metadata.tags)

    const response = await this.client.post('/api/v1/ingest/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      _skipErrorHandling: true, // Skip global error handling for upload
    })

    return response.data
  }

  async getDocuments(params: {
    page?: number
    page_size?: number
    file_type?: string
    status?: string
    search?: string
  } = {}) {
    const response = await this.client.get('/api/v1/ingest/documents', { params })
    return response.data
  }

  async getDocument(documentId: string) {
    const response = await this.client.get(`/api/v1/ingest/documents/${documentId}`)
    return response.data
  }

  async deleteDocument(documentId: string) {
    const response = await this.client.delete(`/api/v1/ingest/documents/${documentId}`)
    return response.data
  }

  async getIngestionStatus(jobId: string) {
    const response = await this.client.get(`/api/v1/ingest/status/${jobId}`)
    return response.data
  }

  async getIngestionStats() {
    const response = await this.client.get('/api/v1/ingest/stats')
    return response.data
  }

  async reprocessDocument(documentId: string) {
    const response = await this.client.post(`/api/v1/ingest/reprocess/${documentId}`)
    return response.data
  }

  // Health check
  async healthCheck() {
    const response = await this.client.get('/health')
    return response.data
  }

  // Generic request method
  async request<T = any>(config: AxiosRequestConfig): Promise<T> {
    const response = await this.client.request<T>(config)
    return response.data
  }
}

export const apiClient = new ApiClient()
export default apiClient