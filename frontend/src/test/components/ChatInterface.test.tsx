import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ChatPage from '@/pages/ChatPage'
import { websocketService } from '@/services/websocket'

// Mock websocket service
vi.mock('@/services/websocket', () => ({
  websocketService: {
    connect: vi.fn().mockResolvedValue(undefined),
    disconnect: vi.fn(),
    sendQuery: vi.fn(),
    isConnected: vi.fn().mockReturnValue(true),
    on: vi.fn(),
    off: vi.fn(),
  },
}))

// Mock react-router-dom
const mockedNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockedNavigate,
    useParams: () => ({ sessionId: 'test-session' }),
  }
})

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
  },
}))

const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: { retry: false },
    mutations: { retry: false },
  },
})

const renderWithProviders = (ui: React.ReactElement) => {
  const testQueryClient = createTestQueryClient()
  return render(
    <QueryClientProvider client={testQueryClient}>
      <BrowserRouter>
        {ui}
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('ChatPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders chat interface elements', () => {
    renderWithProviders(<ChatPage />)

    expect(screen.getByPlaceholderText(/ask a question about your documents/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /send message/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /new chat/i })).toBeInTheDocument()
  })

  it('sends message when form is submitted', async () => {
    renderWithProviders(<ChatPage />)

    const input = screen.getByPlaceholderText(/ask a question about your documents/i)
    const sendButton = screen.getByRole('button', { name: /send message/i })

    fireEvent.change(input, { target: { value: 'What is machine learning?' } })
    fireEvent.click(sendButton)

    await waitFor(() => {
      expect(websocketService.sendQuery).toHaveBeenCalledWith('What is machine learning?', undefined)
    })
  })

  it('clears input after sending message', async () => {
    renderWithProviders(<ChatPage />)

    const input = screen.getByPlaceholderText(/ask a question about your documents/i) as HTMLInputElement
    const sendButton = screen.getByRole('button', { name: /send message/i })

    fireEvent.change(input, { target: { value: 'Test question' } })
    expect(input.value).toBe('Test question')

    fireEvent.click(sendButton)

    await waitFor(() => {
      expect(input.value).toBe('')
    })
  })

  it('disables send button when input is empty', () => {
    renderWithProviders(<ChatPage />)

    const sendButton = screen.getByRole('button', { name: /send message/i })
    expect(sendButton).toBeDisabled()

    const input = screen.getByPlaceholderText(/ask a question about your documents/i)
    fireEvent.change(input, { target: { value: 'Test question' } })

    expect(sendButton).not.toBeDisabled()
  })

  it('sends message when Enter key is pressed without Shift', async () => {
    renderWithProviders(<ChatPage />)

    const input = screen.getByPlaceholderText(/ask a question about your documents/i)
    const sendButton = screen.getByRole('button', { name: /send message/i })

    fireEvent.change(input, { target: { value: 'Test question' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    await waitFor(() => {
      expect(websocketService.sendQuery).toHaveBeenCalledWith('Test question', undefined)
    })
  })

  it('does not send message when Enter+Shift is pressed (allows newline)', () => {
    renderWithProviders(<ChatPage />)

    const input = screen.getByPlaceholderText(/ask a question about your documents/i)
    fireEvent.change(input, { target: { value: 'Line 1\n' } })
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: true })

    expect(websocketService.sendQuery).not.toHaveBeenCalled()
  })

  it('shows loading state while sending message', async () => {
    renderWithProviders(<ChatPage />)

    const input = screen.getByPlaceholderText(/ask a question about your documents/i)
    const sendButton = screen.getByRole('button', { name: /send message/i })

    fireEvent.change(input, { target: { value: 'Test question' } })
    fireEvent.click(sendButton)

    // Check for loading state
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument()
    expect(sendButton).toBeDisabled()
  })

  it('displays received messages', async () => {
    renderWithProviders(<ChatPage />)

    // Simulate receiving a message
    const messageHandler = websocketService.on.mock.calls[0][1]
    messageHandler({
      type: 'response',
      data: {
        content: 'This is a response about machine learning.',
        sources: [],
      },
    })

    await waitFor(() => {
      expect(screen.getByText(/this is a response about machine learning/i)).toBeInTheDocument()
    })
  })

  it('displays sources when provided', async () => {
    renderWithProviders(<ChatPage />)

    // Simulate receiving a message with sources
    const messageHandler = websocketService.on.mock.calls[0][1]
    messageHandler({
      type: 'response',
      data: {
        content: 'Answer with sources',
        sources: [
          {
            document_id: 'doc-1',
            title: 'Machine Learning Guide',
            content: 'Machine learning is...',
            score: 0.95,
          },
        ],
      },
    })

    await waitFor(() => {
      expect(screen.getByText(/machine learning guide/i)).toBeInTheDocument()
      expect(screen.getByText(/95%/i)).toBeInTheDocument()
    })
  })

  it('handles connection errors gracefully', async () => {
    // Mock connection failure
    vi.mocked(websocketService.connect).mockRejectedValue(new Error('Connection failed'))

    renderWithProviders(<ChatPage />)

    await waitFor(() => {
      expect(screen.getByText(/connection error/i)).toBeInTheDocument()
    })
  })

  it('creates new chat session', () => {
    renderWithProviders(<ChatPage />)

    const newChatButton = screen.getByRole('button', { name: /new chat/i })
    fireEvent.click(newChatButton)

    expect(mockedNavigate).toHaveBeenCalledWith('/chat')
  })

  it('handles file upload for context', async () => {
    renderWithProviders(<ChatPage />)

    const fileInput = screen.getByLabelText(/upload file for context/i)
    const file = new File(['test content'], 'test.txt', { type: 'text/plain' })

    fireEvent.change(fileInput, { target: { files: [file] } })

    await waitFor(() => {
      expect(screen.getByText(/test\.txt/i)).toBeInTheDocument()
    })
  })

  it('adjusts textarea height based on content', () => {
    renderWithProviders(<ChatPage />)

    const input = screen.getByPlaceholderText(/ask a question about your documents/i) as HTMLTextAreaElement

    // Initial height
    const initialHeight = input.style.height

    // Add long text
    fireEvent.change(input, { target: { value: 'Line 1\nLine 2\nLine 3\nLine 4\nLine 5' } })

    // Height should have increased
    expect(input.style.height).not.toBe(initialHeight)
  })

  it('shows typing indicator when receiving streaming response', async () => {
    renderWithProviders(<ChatPage />)

    // Simulate start of streaming response
    const messageHandler = websocketService.on.mock.calls[0][1]
    messageHandler({
      type: 'query_start',
      data: {},
    })

    await waitFor(() => {
      expect(screen.getByTestId('typing-indicator')).toBeInTheDocument()
    })

    // Simulate end of streaming response
    messageHandler({
      type: 'response',
      data: {
        content: 'Complete response',
        sources: [],
      },
    })

    await waitFor(() => {
      expect(screen.queryByTestId('typing-indicator')).not.toBeInTheDocument()
    })
  })
})