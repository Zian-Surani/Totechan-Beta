import Cookies from 'js-cookie'
import { WebSocketMessage } from '@/types'

export class WebSocketService {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private messageHandlers: Map<string, ((data: any) => void)[]> = new Map()
  private connectionPromise: Promise<void> | null = null

  constructor() {
    this.setupGlobalHandlers()
  }

  private setupGlobalHandlers() {
    // Handle page visibility changes
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
          this.pauseConnection()
        } else {
          this.resumeConnection()
        }
      })

      // Handle page unload
      window.addEventListener('beforeunload', () => {
        this.disconnect()
      })
    }
  }

  async connect(sessionId: string): Promise<void> {
    if (this.connectionPromise) {
      return this.connectionPromise
    }

    this.connectionPromise = new Promise((resolve, reject) => {
      try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const wsUrl = `${protocol}//${window.location.host}/api/v1/chat/ws/${sessionId}`

        this.ws = new WebSocket(wsUrl)

        this.ws.onopen = () => {
          console.log('WebSocket connected')
          this.reconnectAttempts = 0
          this.connectionPromise = null
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data)
            this.handleMessage(message)
          } catch (error) {
            console.error('Error parsing WebSocket message:', error)
          }
        }

        this.ws.onclose = (event) => {
          console.log('WebSocket disconnected:', event.code, event.reason)
          this.ws = null
          this.connectionPromise = null

          // Attempt to reconnect if not a normal closure
          if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect(sessionId)
          }
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          this.connectionPromise = null
          reject(error)
        }

        // Add authentication token
        const token = Cookies.get('access_token')
        if (token && this.ws) {
          // Send authentication message
          this.ws.send(JSON.stringify({
            type: 'auth',
            data: { token }
          }))
        }

      } catch (error) {
        this.connectionPromise = null
        reject(error)
      }
    })

    return this.connectionPromise
  }

  private scheduleReconnect(sessionId: string) {
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts)

    setTimeout(() => {
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++
        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
        this.connect(sessionId).catch(error => {
          console.error('Reconnection failed:', error)
        })
      }
    }, delay)
  }

  disconnect() {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }
    this.connectionPromise = null
    this.reconnectAttempts = 0
  }

  private pauseConnection() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.close(1000, 'Page hidden')
    }
  }

  private resumeConnection() {
    // Connection will be re-established when needed
  }

  // Message handling
  on(messageType: string, handler: (data: any) => void) {
    if (!this.messageHandlers.has(messageType)) {
      this.messageHandlers.set(messageType, [])
    }
    this.messageHandlers.get(messageType)!.push(handler)

    // Return unsubscribe function
    return () => {
      const handlers = this.messageHandlers.get(messageType)
      if (handlers) {
        const index = handlers.indexOf(handler)
        if (index > -1) {
          handlers.splice(index, 1)
        }
      }
    }
  }

  off(messageType: string, handler?: (data: any) => void) {
    if (handler) {
      const handlers = this.messageHandlers.get(messageType)
      if (handlers) {
        const index = handlers.indexOf(handler)
        if (index > -1) {
          handlers.splice(index, 1)
        }
      }
    } else {
      this.messageHandlers.delete(messageType)
    }
  }

  private handleMessage(message: WebSocketMessage) {
    const handlers = this.messageHandlers.get(message.type)
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(message.data)
        } catch (error) {
          console.error(`Error in handler for message type ${message.type}:`, error)
        }
      })
    }

    // Log unhandled message types
    if (!handlers && message.type !== 'pong') {
      console.log('Unhandled WebSocket message:', message)
    }
  }

  // Send messages
  send(message: Partial<WebSocketMessage>) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const fullMessage: WebSocketMessage = {
        type: 'query',
        data: {},
        timestamp: new Date().toISOString(),
        ...message
      }
      this.ws.send(JSON.stringify(fullMessage))
    } else {
      console.warn('WebSocket not connected, cannot send message:', message)
    }
  }

  sendQuery(query: string, retrievalConfig?: any) {
    this.send({
      type: 'query',
      data: {
        query,
        retrieval_config: retrievalConfig
      }
    })
  }

  ping() {
    this.send({
      type: 'ping',
      data: {}
    })
  }

  // Connection status
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }

  isConnecting(): boolean {
    return this.connectionPromise !== null
  }

  getConnectionState(): string {
    if (!this.ws) return 'disconnected'

    switch (this.ws.readyState) {
      case WebSocket.CONNECTING: return 'connecting'
      case WebSocket.OPEN: return 'connected'
      case WebSocket.CLOSING: return 'closing'
      case WebSocket.CLOSED: return 'disconnected'
      default: return 'unknown'
    }
  }
}

// Singleton instance
export const websocketService = new WebSocketService()
export default websocketService