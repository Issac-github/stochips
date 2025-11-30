import cors from 'cors'
import express from 'express'
import { randomUUID } from 'node:crypto'
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js'
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js'
import { isInitializeRequest } from '@modelcontextprotocol/sdk/types.js'
import { errorLog } from '@shared/logger'

/*
  Initialize HTTP Transport with both modern and legacy endpoints
*/
const initHttpTransport = (params: { server: McpServer; port: number }) => {
  const { server, port } = params
  const app = express()
  app.use(
    cors({
      origin: '*',
      exposedHeaders: ['Mcp-Session-Id']
    })
  )
  app.use(express.json())

  // Store transports for each session type
  const transports = {
    streamable: {} as Record<string, StreamableHTTPServerTransport>,
    sse: {} as Record<string, SSEServerTransport>
  }

  /*
    1. Modern Streamable HTTP endpoint without session ID
  */
  app.all('/mcp', async (req, res) => {
    // Create a new transport for each request to prevent request ID collisions
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined,
      enableJsonResponse: true
    })
    res.on('close', () => {
      transport.close()
    })
    await server.connect(transport)
    await transport.handleRequest(req, res, req.body)
  })

  /*
    2. Modern Streamable HTTP endpoint with session ID
  */
  // Handle POST requests for client-to-server communication
  app.post('/session', async (req, res) => {
    const sessionId = req.headers['mcp-session-id'] as string | undefined
    let transport: StreamableHTTPServerTransport
    if (sessionId && transports[sessionId]) {
      transport = transports[sessionId]
    } else if (!sessionId && isInitializeRequest(req.body)) {
      transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: () => randomUUID(),
        onsessioninitialized: (sessionId) => {
          transports[sessionId] = transport
        }
      })
      transport.onclose = () => {
        if (transport.sessionId) {
          delete transports[transport.sessionId]
        }
      }
      await server.connect(transport)
    } else {
      res.status(400).json({
        jsonrpc: '2.0',
        error: {
          code: -32000,
          message: 'Bad Request: No valid session ID provided'
        },
        id: null
      })
      return
    }
    await transport.handleRequest(req, res, req.body)
  })
  // Reusable handler for GET and DELETE requests
  const handleSessionRequest = async (
    req: express.Request,
    res: express.Response
  ) => {
    const sessionId = req.headers['mcp-session-id'] as string | undefined
    if (!sessionId || !transports[sessionId]) {
      res.status(400).send('Invalid or missing session ID')
      return
    }
    const transport = transports[sessionId]
    await transport.handleRequest(req, res)
  }
  app.get('/session', handleSessionRequest)
  app.delete('/session', handleSessionRequest)

  /*
    3. Legacy SSE endpoint for older clients
  */
  app.get('/sse', async (_req, res) => {
    // Create SSE transport for legacy clients
    const transport = new SSEServerTransport('/sse/messages', res)
    transports.sse[transport.sessionId] = transport
    res.on('close', () => {
      delete transports.sse[transport.sessionId]
    })

    await server.connect(transport)
  })

  // Legacy message endpoint for older clients
  app.post('/sse/messages', async (req, res) => {
    const sessionId = req.query.sessionId as string
    const transport = transports.sse[sessionId]
    if (transport) {
      await transport.handlePostMessage(req, res, req.body)
    } else {
      res.status(400).send('No transport found for sessionId')
    }
  })

  app.listen(port, (error) => {
    if (error) {
      errorLog(`Failed to start HTTP server: ${error.message}`)
    } else {
      errorLog(`HTTP server listening on http://localhost:${port}`)
    }
  })
}

export default initHttpTransport
