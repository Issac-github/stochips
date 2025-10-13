import cors from 'cors'
import { randomUUID } from 'crypto'
import express from 'express'
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js'
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js'
import { errorLog } from '@shared/logger'

/*
  Initialize HTTP Transport with both modern and legacy endpoints
*/
export const initHttpTransport = (params: {
  server: McpServer
  port: number
}) => {
  const { server, port } = params
  const app = express()

  // Apply CORS to all routes
  app.use(
    cors({
      origin: '*', // Allow all origins
      exposedHeaders: ['Mcp-Session-Id']
    })
  )

  // Only parse JSON for non-streamable endpoints
  app.use((req, res, next) => {
    if (req.path === '/mcp') {
      // Don't parse JSON for streamable HTTP endpoint - it needs raw stream
      next()
    } else {
      express.json()(req, res, next)
    }
  })

  // Store transports for each session type
  const transports = {
    streamable: {} as Record<string, StreamableHTTPServerTransport>,
    sse: {} as Record<string, SSEServerTransport>
  }

  // Modern Streamable HTTP endpoint
  app.all('/mcp', async (req, res) => {
    try {
      // Get session ID from header
      const sessionId = req.headers['mcp-session-id'] as string | undefined

      let transport: StreamableHTTPServerTransport

      if (sessionId && transports.streamable[sessionId]) {
        // Reuse existing transport for this session
        transport = transports.streamable[sessionId]
      } else {
        // Create new transport for new session
        transport = new StreamableHTTPServerTransport({
          sessionIdGenerator: () => randomUUID(),
          onsessioninitialized: (newSessionId: string) => {
            transports.streamable[newSessionId] = transport
          },
          onsessionclosed: (closedSessionId: string) => {
            delete transports.streamable[closedSessionId]
          }
        })

        // Connect to server
        await server.connect(transport)
      }

      // Handle the request
      await transport.handleRequest(req, res)
    } catch (error) {
      errorLog(
        'Streamable HTTP connection failed, falling back to SSE transport',
        error
      )
      res.status(500).send('Internal server error')
    }
  })

  // Legacy SSE endpoint for older clients
  app.get('/sse', async (_req, res) => {
    // Create SSE transport for legacy clients
    const transport = new SSEServerTransport('/messages', res)
    const sessionId = transport.sessionId
    if (sessionId) {
      transports.sse[sessionId] = transport

      res.on('close', () => {
        if (sessionId) {
          delete transports.sse[sessionId]
        }
      })
    }

    await server.connect(transport)
  })

  // Legacy message endpoint for older clients
  app.post('/messages', async (req, res) => {
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
