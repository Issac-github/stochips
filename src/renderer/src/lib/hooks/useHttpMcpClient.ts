import { useEffect, useRef, useState } from 'react'
import { Client } from '@modelcontextprotocol/sdk/client/index.js'
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js'
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js'
import { debugLog, errorLog } from '@shared/logger'

interface Props {
  addMessage: (message: {
    type: 'user' | 'assistant' | 'system'
    content: string
    error?: boolean
  }) => void
}

const useHttpMcpClient = ({ addMessage }: Props) => {
  const clientRef = useRef<Client | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [port, setPort] = useState<number | null>(null)
  const [connectionError, setConnectionError] = useState<string | null>(null)

  const connectClient = async () => {
    const streamableHttpWithoutSessionId = new URL(
      `http://localhost:${port}/mcp`
    )
    const streamableHttpWithSessionId = new URL(
      `http://localhost:${port}/session`
    )
    const sseUrl = new URL(`http://localhost:${port}/sse`)
    if (!port) {
      throw new Error('MCP port not available')
    }
    try {
      addMessage({
        type: 'system',
        content: 'Connecting to Streamable MCP server...'
      })
      clientRef.current = new Client({
        name: 'streamable-http-client',
        version: '1.0.0'
      })
      const transport = new StreamableHTTPClientTransport(
        Math.random() > 0.5
          ? streamableHttpWithSessionId
          : streamableHttpWithoutSessionId
      )
      // streamableHttpWithSessionId or streamableHttpWithoutSessionId
      debugLog('Connecting using Streamable HTTP transport')
      await clientRef.current.connect(transport)
      const sessionId = transport.sessionId
      debugLog('Transport created with session ID:', sessionId)
      debugLog('Connected to MCP server')
      debugLog('Connected using Streamable HTTP transport')
      setIsConnected(true)
      setConnectionError(null)
      addMessage({
        type: 'system',
        content: '✅ Connected to Streamable MCP server successfully!'
      })
    } catch (error) {
      addMessage({
        type: 'system',
        content: `❌ Streamable SSE Connection failed: ${error instanceof Error ? error.message : 'Connection failed'}`,
        error: true
      })
      try {
        // If that fails with a 4xx error, try the older SSE transport
        addMessage({
          type: 'system',
          content: 'Connecting to SSE MCP server...'
        })
        errorLog(
          'Streamable HTTP connection failed, falling back to SSE transport',
          error
        )
        clientRef.current = new Client({
          name: 'sse-client',
          version: '1.0.0'
        })
        const sseTransport = new SSEClientTransport(sseUrl)
        debugLog('Connecting using SSE transport')
        await clientRef.current.connect(sseTransport)
        debugLog('Connected using SSE transport')
        setIsConnected(true)
        setConnectionError(null)
        addMessage({
          type: 'system',
          content: '✅ Connected to SSE MCP server successfully!'
        })
      } catch (sseError) {
        errorLog('SSE connection failed', sseError)
        setIsConnected(false)
        setConnectionError(
          sseError instanceof Error ? sseError.message : 'Connection failed'
        )
        addMessage({
          type: 'system',
          content: `❌ SSE Connection failed: ${sseError instanceof Error ? sseError.message : 'Connection failed'}`,
          error: true
        })
      }
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
      setPort(portMap.http)
    })
    return () => {
      unsubscribe()
    }
  }, [])

  return {
    isConnected,
    connectionError,
    setConnectionError,
    clientRef
  }
}

export default useHttpMcpClient
