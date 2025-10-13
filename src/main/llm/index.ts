import { WebSocketServer } from 'ws'
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { debugLog, errorLog } from '@shared/logger'
import { WebSocketTransport, initGPTChat, initHttpTransport } from './mcp'
import registerTools from './mcp/tools'

const getAvailablePorts = async (
  count: number,
  startPort: number = 3336
): Promise<number[]> => {
  const { default: getPort } = await import('get-port')
  const ports: number[] = []
  const usedPorts = new Set<number>()

  while (ports.length < count) {
    const port = await getPort({
      port: startPort + ports.length,
      exclude: Array.from(usedPorts)
    })
    usedPorts.add(port)
    ports.push(port)
  }
  return ports
}

const initLLMServer = async (): Promise<{
  SOCKETPORT: number
  HTTPPORT: number
  GPTPORT: number
}> => {
  try {
    const [SOCKETPORT, HTTPPORT, GPTPORT] = await getAvailablePorts(3)

    // MCP WebSocket 服务器
    const socketServer = new McpServer(
      {
        name: 'mcp-json-filter',
        version: '0.1.0'
      },
      { capabilities: {} }
    )
    registerTools(socketServer)
    const wss = new WebSocketServer({
      port: SOCKETPORT,
      handleProtocols: (protocols) => (protocols.has('mcp') ? 'mcp' : false)
    })
    debugLog(`[MCP] WebSocket server listening on ws://localhost:${SOCKETPORT}`)
    wss.on('connection', (socket) => {
      const transport = new WebSocketTransport(socket)
      socketServer.connect(transport)
    })

    // MCP HTTP 服务器
    const httpServer = new McpServer(
      {
        name: 'mcp-http',
        version: '0.1.0'
      },
      { capabilities: {} }
    )
    registerTools(httpServer)
    initHttpTransport({
      server: httpServer,
      port: HTTPPORT
    })
    debugLog(`[MCP] HTTP server listening on http://localhost:${HTTPPORT}`)

    // GPT HTTP 服务器
    initGPTChat({
      port: GPTPORT
    })
    debugLog(`[GPT] HTTP server listening on http://localhost:${GPTPORT}`)

    return { SOCKETPORT, HTTPPORT, GPTPORT }
  } catch (error) {
    errorLog(error)
    throw error
  }
}

export default initLLMServer
