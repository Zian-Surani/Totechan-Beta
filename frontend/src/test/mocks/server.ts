import { setupServer } from 'msw/node'
import { rest } from 'msw'
import { API_BASE_URL } from '@/services/api'

// Mock user data
const mockUser = {
  id: '1',
  email: 'test@example.com',
  first_name: 'Test',
  last_name: 'User',
  is_active: true,
  is_verified: true,
  created_at: '2024-01-01T00:00:00Z',
}

// Mock auth responses
export const handlers = [
  // Authentication endpoints
  rest.post(`${API_BASE_URL}/api/v1/auth/register`, (req, res, ctx) => {
    return res(
      ctx.status(201),
      ctx.json({
        success: true,
        data: {
          user: mockUser,
          access_token: 'mock-token',
          expires_in: 3600,
        },
      })
    )
  }),

  rest.post(`${API_BASE_URL}/api/v1/auth/token`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        access_token: 'mock-token',
        expires_in: 3600,
      })
    )
  }),

  rest.get(`${API_BASE_URL}/api/v1/auth/me`, (req, res, ctx) => {
    const authHeader = req.headers.get('Authorization')
    if (!authHeader?.includes('Bearer mock-token')) {
      return res(ctx.status(401), ctx.json({ detail: 'Not authenticated' }))
    }

    return res(
      ctx.status(200),
      ctx.json({
        success: true,
        data: mockUser,
      })
    )
  }),

  rest.post(`${API_BASE_URL}/api/v1/auth/refresh`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        access_token: 'new-mock-token',
      })
    )
  }),

  rest.post(`${API_BASE_URL}/api/v1/auth/logout`, (req, res, ctx) => {
    return res(ctx.status(200))
  }),

  // Chat endpoints
  rest.post(`${API_BASE_URL}/api/v1/chat/ask`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        success: true,
        data: {
          answer: 'This is a mock answer about machine learning.',
          sources: [
            {
              document_id: 'doc-1',
              title: 'Introduction to Machine Learning',
              content: 'Machine learning is a subset of artificial intelligence...',
              score: 0.95,
              metadata: {},
            },
          ],
          session_id: 'session-123',
          query: 'What is machine learning?',
          response_time: 1.2,
        },
      })
    )
  }),

  rest.get(`${API_BASE_URL}/api/v1/chat/sessions`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        success: true,
        data: {
          sessions: [
            {
              id: 'session-1',
              title: 'Machine Learning Discussion',
              description: 'Discussion about ML concepts',
              is_active: true,
              created_at: '2024-01-01T00:00:00Z',
              updated_at: '2024-01-01T00:30:00Z',
              message_count: 5,
            },
          ],
          pagination: {
            page: 1,
            page_size: 10,
            total: 1,
            total_pages: 1,
          },
        },
      })
    )
  }),

  rest.post(`${API_BASE_URL}/api/v1/chat/sessions`, (req, res, ctx) => {
    return res(
      ctx.status(201),
      ctx.json({
        success: true,
        data: {
          id: 'session-123',
          title: 'New Chat Session',
          description: 'A new chat session',
          is_active: true,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
          message_count: 0,
        },
      })
    )
  }),

  rest.get(`${API_BASE_URL}/api/v1/chat/sessions/:sessionId/history`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        success: true,
        data: {
          messages: [
            {
              id: 'msg-1',
              session_id: 'session-1',
              content: 'What is machine learning?',
              message_type: 'human',
              created_at: '2024-01-01T00:00:00Z',
            },
            {
              id: 'msg-2',
              session_id: 'session-1',
              content: 'Machine learning is a subset of artificial intelligence...',
              message_type: 'ai',
              created_at: '2024-01-01T00:00:05Z',
              sources: [],
            },
          ],
          pagination: {
            page: 1,
            page_size: 50,
            total: 2,
            total_pages: 1,
          },
        },
      })
    )
  }),

  // Document endpoints
  rest.get(`${API_BASE_URL}/api/v1/ingest/documents`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        success: true,
        data: {
          documents: [
            {
              id: 'doc-1',
              title: 'Machine Learning Basics',
              description: 'Introduction to ML concepts',
              file_type: 'pdf',
              file_size: 1024000,
              status: 'processed',
              created_at: '2024-01-01T00:00:00Z',
              updated_at: '2024-01-01T00:10:00Z',
            },
          ],
          pagination: {
            page: 1,
            page_size: 10,
            total: 1,
            total_pages: 1,
          },
        },
      })
    )
  }),

  rest.post(`${API_BASE_URL}/api/v1/ingest/upload`, (req, res, ctx) => {
    return res(
      ctx.status(202),
      ctx.json({
        success: true,
        data: {
          document_id: 'doc-123',
          job_id: 'job-123',
          status: 'processing',
        },
      })
    )
  }),

  rest.get(`${API_BASE_URL}/api/v1/ingest/status/:jobId`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        success: true,
        data: {
          job_id: 'job-123',
          status: 'completed',
          progress: 100,
          message: 'Document processed successfully',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:05:00Z',
        },
      })
    )
  }),

  rest.get(`${API_BASE_URL}/api/v1/ingest/stats`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        success: true,
        data: {
          total_documents: 10,
          processed_documents: 8,
          failed_documents: 1,
          processing_documents: 1,
          total_chunks: 150,
          total_size: 10485760, // 10MB
        },
      })
    )
  }),

  // Health check
  rest.get(`${API_BASE_URL}/health`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        status: 'healthy',
        timestamp: '2024-01-01T00:00:00Z',
        version: '1.0.0',
        services: {
          database: 'healthy',
          redis: 'healthy',
          vector_db: 'healthy',
        },
      })
    )
  }),
]

// Create MSW server
export const server = setupServer(...handlers)