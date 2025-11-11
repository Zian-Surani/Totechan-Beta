import React, { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { SendIcon, PaperClipIcon, DocumentTextIcon, PlusIcon } from '@heroicons/react/24/outline'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import apiClient from '@/services/api'
import websocketService from '@/services/websocket'
import { Message, ChatSession, SourceCitation } from '@/types'
import { ChatMessage } from '@/components/Chat/ChatMessage'
import { MessageInput } from '@/components/Chat/MessageInput'
import { SourceCitation as SourceCitationComponent } from '@/components/Chat/SourceCitation'
import toast from 'react-hot-toast'

export default function ChatPage() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [currentStreamingMessage, setCurrentStreamingMessage] = useState('')
  const [currentSources, setCurrentSources] = useState<SourceCitation[]>([])
  const [isWebSocketConnected, setIsWebSocketConnected] = useState(false)

  // Queries
  const { data: session, isLoading: sessionLoading } = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => sessionId ? apiClient.getSession(sessionId) : null,
    enabled: !!sessionId,
  })

  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ['session-history', sessionId],
    queryFn: () => sessionId ? apiClient.getSessionHistory(sessionId) : null,
    enabled: !!sessionId,
  })

  // Mutations
  const askQuestionMutation = useMutation({
    mutationFn: apiClient.askQuestion,
    onSuccess: (data) => {
      // Add assistant message
      const assistantMessage: Message = {
        id: data.message_id,
        session_id: data.session_id,
        role: 'assistant',
        content: data.answer,
        sources: data.sources,
        model_used: data.model_used,
        token_count: data.usage.total_tokens,
        status: 'completed',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }
      setMessages(prev => [...prev, assistantMessage])
      setIsTyping(false)
    },
    onError: (error: any) => {
      setIsTyping(false)
      toast.error('Failed to get response. Please try again.')
    },
  })

  const createSessionMutation = useMutation({
    mutationFn: apiClient.createSession,
    onSuccess: (data) => {
      navigate(`/chat/${data.id}`)
    },
    onError: () => {
      toast.error('Failed to create new session')
    },
  })

  // Initialize session
  useEffect(() => {
    if (session && !sessionLoading) {
      setCurrentSession(session)
    }
  }, [session, sessionLoading])

  // Load messages
  useEffect(() => {
    if (history?.messages && !historyLoading) {
      setMessages(history.messages)
    }
  }, [history, historyLoading])

  // WebSocket setup
  useEffect(() => {
    if (sessionId && !isWebSocketConnected) {
      websocketService.connect(sessionId).then(() => {
        setIsWebSocketConnected(true)
      }).catch(() => {
        console.log('WebSocket connection failed, falling back to HTTP')
      })
    }

    return () => {
      if (sessionId) {
        websocketService.disconnect()
        setIsWebSocketConnected(false)
      }
    }
  }, [sessionId])

  // WebSocket message handlers
  useEffect(() => {
    const unsubscribers = [
      websocketService.on('status', (data) => {
        setIsTyping(data.status === 'thinking')
      }),

      websocketService.on('sources', (data) => {
        setCurrentSources(data.sources)
      }),

      websocketService.on('message_chunk', (data) => {
        setCurrentStreamingMessage(prev => prev + data.content)
      }),

      websocketService.on('complete', (data) => {
        const assistantMessage: Message = {
          id: Date.now().toString(),
          session_id: sessionId!,
          role: 'assistant',
          content: data.content,
          sources: data.sources,
          status: 'completed',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }
        setMessages(prev => [...prev, assistantMessage])
        setCurrentStreamingMessage('')
        setCurrentSources([])
        setIsTyping(false)
      }),

      websocketService.on('error', (data) => {
        toast.error(data.message)
        setIsTyping(false)
        setCurrentStreamingMessage('')
        setCurrentSources([])
      }),
    ]

    return () => {
      unsubscribers.forEach(unsubscribe => unsubscribe())
    }
  }, [sessionId])

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, currentStreamingMessage])

  const handleSendMessage = async (message: string) => {
    if (!message.trim()) return

    // If no session, create one
    if (!sessionId) {
      await createSessionMutation.mutateAsync()
      return
    }

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      session_id: sessionId!,
      role: 'user',
      content: message.trim(),
      status: 'completed',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsTyping(true)

    // Use WebSocket if available, otherwise HTTP
    if (isWebSocketConnected) {
      websocketService.sendQuery(message, {
        k: 8,
        rerank: true,
      })
    } else {
      askQuestionMutation.mutate({
        query: message,
        session_id: sessionId!,
        retrieval_config: {
          k: 8,
          rerank: true,
        },
      })
    }
  }

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      navigate('/documents', {
        state: { uploadFile: file }
      })
    }
  }

  const createNewSession = () => {
    createSessionMutation.mutate()
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-4 sm:px-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <button
              onClick={createNewSession}
              className="mr-4 p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              title="New chat"
            >
              <PlusIcon className="h-5 w-5" />
            </button>
            <div>
              <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
                {currentSession?.title || 'New Chat'}
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {currentSession?.description || 'Ask questions about your documents'}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              title="Upload document"
            >
              <PaperClipIcon className="h-5 w-5" />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.html,.txt"
              onChange={handleFileUpload}
              className="hidden"
            />
          </div>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto">
        <div className="px-4 py-6 sm:px-6 space-y-4">
          {messages.length === 0 && !isTyping && (
            <div className="text-center py-12">
              <DocumentTextIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">
                No messages yet
              </h3>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Start a conversation by asking a question about your uploaded documents.
              </p>
            </div>
          )}

          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}

          {/* Streaming message */}
          {currentStreamingMessage && (
            <div className="flex justify-start">
              <div className="message-assistant max-w-3xl">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {currentStreamingMessage}
                </ReactMarkdown>
                <div className="loading-spinner h-4 w-4 mt-2"></div>
              </div>
            </div>
          )}

          {/* Current sources */}
          {currentSources.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Sources:</p>
              <div className="flex flex-wrap gap-2">
                {currentSources.map((source, index) => (
                  <SourceCitationComponent key={index} source={source} />
                ))}
              </div>
            </div>
          )}

          {/* Typing indicator */}
          {isTyping && !currentStreamingMessage && (
            <div className="flex justify-start">
              <div className="message-assistant">
                <div className="flex items-center space-x-2">
                  <div className="loading-spinner h-4 w-4"></div>
                  <span className="text-sm">Thinking...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input area */}
      <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-4 sm:px-6">
        <MessageInput
          value={inputValue}
          onChange={setInputValue}
          onSend={handleSendMessage}
          disabled={isTyping || createSessionMutation.isPending}
          placeholder={
            sessionId
              ? "Ask a question about your documents..."
              : "Start by creating a new session..."
          }
        />
      </div>
    </div>
  )
}