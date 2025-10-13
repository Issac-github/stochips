import { useEffect, useRef, useState } from 'react'
import { Client } from '@modelcontextprotocol/sdk/client/index.js'
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js'
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js'
import { debugLog, errorLog } from '@shared/logger'

const useHttpMcpClient = () => {
  const clientRef = useRef<Client | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [port, setPort] = useState<number | null>(null)
  const [connectionError, setConnectionError] = useState<string | null>(null)

  const connectClient = async () => {
    const baseUrl = new URL(`http://localhost:${port}/mcp`)
    if (!port) {
      throw new Error('MCP port not available')
    }
    try {
      clientRef.current = new Client({
        name: 'streamable-http-client',
        version: '1.0.0'
      })
      const transport = new StreamableHTTPClientTransport(baseUrl)
      await clientRef.current.connect(transport)
      const sessionId = transport.sessionId
      debugLog('Transport created with session ID:', sessionId)
      debugLog('Connected to MCP server')
      debugLog('Connected using Streamable HTTP transport')
      setIsConnected(true)
      setConnectionError(null)
    } catch (error) {
      try {
        // If that fails with a 4xx error, try the older SSE transport
        errorLog(
          'Streamable HTTP connection failed, falling back to SSE transport',
          error
        )
        clientRef.current = new Client({
          name: 'sse-client',
          version: '1.0.0'
        })
        const sseTransport = new SSEClientTransport(baseUrl)
        debugLog('Connecting using SSE transport')
        await clientRef.current.connect(sseTransport)
        debugLog('Connected using SSE transport')
        setIsConnected(true)
        setConnectionError(null)
      } catch (sseError) {
        errorLog('SSE connection failed', sseError)
        setIsConnected(false)
        setConnectionError(
          sseError instanceof Error ? sseError.message : 'Connection failed'
        )
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
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [port])

  useEffect(() => {
    window.api.handleMcpPort.requestMcpPort()
    const unsubscribe = window.api.handleMcpPort.responseMcpPort((portMap) => {
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
