import { useEffect, useRef, useState } from 'react'
import { Client } from '@modelcontextprotocol/sdk/client/index.js'
import { WebSocketClientTransport } from '@modelcontextprotocol/sdk/client/websocket.js'
import { errorLog } from '@shared/logger'

interface Props {
  addMessage: (message: {
    type: 'user' | 'assistant' | 'system'
    content: string
    error?: boolean
  }) => void
}

const useSocketMcpClient = ({ addMessage }: Props) => {
  const clientRef = useRef<Client | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [port, setPort] = useState<number | null>(null)
  const [connectionError, setConnectionError] = useState<string | null>(null)

  const connectClient = async () => {
    if (!port) {
      throw new Error('MCP port not available')
    }
    try {
      setConnectionError(null)
      addMessage({ type: 'system', content: 'Connecting to MCP server...' })
      const client = new Client({ name: 'web-client', version: '0.1.0' })
      const transport = new WebSocketClientTransport(
        new URL(`ws://localhost:${port}`)
      )
      await client.connect(transport)
      clientRef.current = client
      setIsConnected(true)
      addMessage({
        type: 'system',
        content: '✅ Connected to MCP server successfully!'
      })
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Unknown connection error'
      setConnectionError(errorMessage)
      addMessage({
        type: 'system',
        content: `❌ Connection failed: ${errorMessage}`,
        error: true
      })
      errorLog(error)
    }
  }

  useEffect(() => {
    if (!port || clientRef.current) {
      return
    }
    connectClient()
    return () => {
      clientRef.current?.close()
      clientRef.current = null
      setIsConnected(false)
      addMessage({ type: 'system', content: 'Disconnected from MCP server.' })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [port])

  useEffect(() => {
    window.api.mcpPort.request()
    const unsubscribe = window.api.mcpPort.response((portMap) => {
      setPort(portMap.socket)
    })
    return () => {
      unsubscribe()
    }
  }, [])

  return { isConnected, connectionError, setConnectionError, clientRef }
}

export default useSocketMcpClient
