import type { WebSocket as WSWebSocket } from 'ws'
import { SocketReadyState } from '@shared/lib/utils'

/*
  Transport implementation for MCP over WebSocket
*/
class WebSocketTransport {
  socket: WSWebSocket
  onmessage?: (message: unknown) => void
  onerror?: (error: unknown) => void
  onclose?: () => void

  constructor(socket: WSWebSocket) {
    this.socket = socket
  }

  async start(): Promise<void> {
    this.socket.on('message', (data) => {
      try {
        const message = JSON.parse(data.toString())
        this.onmessage?.(message)
      } catch (error) {
        this.onerror?.(error)
      }
    })

    this.socket.on('close', () => {
      this.onclose?.()
    })

    this.socket.on('error', (error) => {
      this.onerror?.(error)
    })
  }

  async send(message: unknown): Promise<void> {
    if (this.socket.readyState === SocketReadyState.Open) {
      this.socket.send(JSON.stringify(message))
    } else {
      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new Error('WebSocket connection timeout'))
        }, 5e3)
        const checkState = () => {
          if (this.socket.readyState === SocketReadyState.Open) {
            clearTimeout(timeout)
            this.socket.send(JSON.stringify(message))
            resolve()
          } else if (this.socket.readyState === SocketReadyState.Closed) {
            clearTimeout(timeout)
            reject(new Error('WebSocket connection closed'))
          } else {
            setTimeout(checkState, 10)
          }
        }
        checkState()
      })
    }
  }

  async close(): Promise<void> {
    this.socket.close()
  }
}

export default WebSocketTransport
