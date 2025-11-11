import { describe, it, expect, vi, beforeEach } from 'vitest'
import { apiClient } from '@/services/api'
import Cookies from 'js-cookie'

// Mock axios
vi.mock('axios', () => ({
  default: class MockAxios {
    constructor() {
      this.interceptors = {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      }
    }

    get = vi.fn()
    post = vi.fn()
    put = vi.fn()
    delete = vi.fn()
    request = vi.fn()
  },
}))

// Mock js-cookie
vi.mock('js-cookie', () => ({
  default: {
    get: vi.fn(),
    set: vi.fn(),
    remove: vi.fn(),
  },
}))

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
  },
}))

describe('ApiClient', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Authentication', () => {
    it('stores token on successful login', async () => {
      const mockResponse = {
        data: {
          access_token: 'test-token',
          expires_in: 3600,
        },
      }

      apiClient.client.post = vi.fn().mockResolvedValue(mockResponse)

      const result = await apiClient.login('test@example.com', 'password')

      expect(Cookies.set).toHaveBeenCalledWith(
        'access_token',
        'test-token',
        expect.objectContaining({
          expires: 0.041666666666666664, // 3600 seconds in days
        })
      )
      expect(result).toEqual(mockResponse.data)
    })

    it('removes token on logout', () => {
      apiClient.client.post = vi.fn().mockResolvedValue({})

      apiClient.logout()

      expect(Cookies.remove).toHaveBeenCalledWith('access_token')
    })

    it('retrieves current user with valid token', async () => {
      const mockUser = { id: 1, email: 'test@example.com' }
      const mockResponse = {
        data: {
          success: true,
          data: mockUser,
        },
      }

      apiClient.client.get = vi.fn().mockResolvedValue(mockResponse)

      const result = await apiClient.getCurrentUser()

      expect(apiClient.client.get).toHaveBeenCalledWith('/api/v1/auth/me')
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('Chat functionality', () => {
    it('sends chat query with retrieval config', async () => {
      const mockResponse = {
        data: {
          success: true,
          data: {
            answer: 'Test answer',
            sources: [],
            session_id: 'session-123',
          },
        },
      }

      apiClient.client.post = vi.fn().mockResolvedValue(mockResponse)

      const query = {
        query: 'What is machine learning?',
        session_id: 'session-123',
        retrieval_config: {
          k: 5,
          rerank: true,
          threshold: 0.7,
        },
      }

      const result = await apiClient.askQuestion(query)

      expect(apiClient.client.post).toHaveBeenCalledWith('/api/v1/chat/ask', query)
      expect(result).toEqual(mockResponse.data)
    })

    it('creates new chat session', async () => {
      const mockSession = {
        id: 'session-123',
        title: 'New Chat',
        created_at: '2024-01-01T00:00:00Z',
      }

      const mockResponse = {
        data: {
          success: true,
          data: mockSession,
        },
      }

      apiClient.client.post = vi.fn().mockResolvedValue(mockResponse)

      const result = await apiClient.createSession({
        title: 'New Chat',
        description: 'A new chat session',
      })

      expect(apiClient.client.post).toHaveBeenCalledWith('/api/v1/chat/sessions', {
        title: 'New Chat',
        description: 'A new chat session',
      })
      expect(result).toEqual(mockResponse.data)
    })

    it('retrieves chat sessions with pagination', async () => {
      const mockResponse = {
        data: {
          success: true,
          data: {
            sessions: [],
            pagination: {
              page: 1,
              page_size: 10,
              total: 0,
              total_pages: 0,
            },
          },
        },
      }

      apiClient.client.get = vi.fn().mockResolvedValue(mockResponse)

      const result = await apiClient.getSessions({
        page: 1,
        page_size: 10,
      })

      expect(apiClient.client.get).toHaveBeenCalledWith('/api/v1/chat/sessions', {
        params: { page: 1, page_size: 10 },
      })
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('Document management', () => {
    it('uploads document with metadata', async () => {
      const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' })
      const mockResponse = {
        data: {
          success: true,
          data: {
            document_id: 'doc-123',
            job_id: 'job-123',
            status: 'processing',
          },
        },
      }

      apiClient.client.post = vi.fn().mockResolvedValue(mockResponse)

      const metadata = {
        title: 'Test Document',
        description: 'A test document',
        access_level: 'private',
        tags: 'test,document',
      }

      const result = await apiClient.uploadDocument(mockFile, metadata)

      expect(apiClient.client.post).toHaveBeenCalledWith(
        '/api/v1/ingest/upload',
        expect.any(FormData),
        expect.objectContaining({
          headers: { 'Content-Type': 'multipart/form-data' },
          _skipErrorHandling: true,
        })
      )
      expect(result).toEqual(mockResponse.data)
    })

    it('retrieves documents with filters', async () => {
      const mockResponse = {
        data: {
          success: true,
          data: {
            documents: [],
            pagination: { page: 1, page_size: 10, total: 0, total_pages: 0 },
          },
        },
      }

      apiClient.client.get = vi.fn().mockResolvedValue(mockResponse)

      const params = {
        page: 1,
        page_size: 10,
        file_type: 'pdf',
        status: 'processed',
        search: 'machine learning',
      }

      const result = await apiClient.getDocuments(params)

      expect(apiClient.client.get).toHaveBeenCalledWith('/api/v1/ingest/documents', {
        params,
      })
      expect(result).toEqual(mockResponse.data)
    })

    it('deletes document', async () => {
      const mockResponse = {
        data: {
          success: true,
          data: { deleted: true },
        },
      }

      apiClient.client.delete = vi.fn().mockResolvedValue(mockResponse)

      const result = await apiClient.deleteDocument('doc-123')

      expect(apiClient.client.delete).toHaveBeenCalledWith('/api/v1/ingest/documents/doc-123')
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('Error handling', () => {
    it('handles 401 unauthorized error', async () => {
      const error = {
        response: { status: 401 },
        config: {},
      }

      apiClient.client.post = vi.fn().mockRejectedValue(error)

      await expect(apiClient.login('test@example.com', 'wrong-password')).rejects.toThrow()

      // Should have attempted token refresh
      expect(apiClient.client.post).toHaveBeenCalledWith('/api/v1/auth/refresh')
    })

    it('handles 500 server error', async () => {
      const error = {
        response: {
          status: 500,
          data: { error: { message: 'Internal server error' } },
        },
        config: {},
      }

      apiClient.client.get = vi.fn().mockRejectedValue(error)

      await expect(apiClient.getCurrentUser()).rejects.toThrow()
    })

    it('handles network errors', async () => {
      const error = {
        message: 'Network Error',
        config: { _skipErrorHandling: false },
      }

      apiClient.client.get = vi.fn().mockRejectedValue(error)

      await expect(apiClient.getCurrentUser()).rejects.toThrow()
    })
  })

  describe('Health check', () => {
    it('performs health check', async () => {
      const mockResponse = {
        data: {
          status: 'healthy',
          timestamp: '2024-01-01T00:00:00Z',
        },
      }

      apiClient.client.get = vi.fn().mockResolvedValue(mockResponse)

      const result = await apiClient.healthCheck()

      expect(apiClient.client.get).toHaveBeenCalledWith('/health')
      expect(result).toEqual(mockResponse.data)
    })
  })
})