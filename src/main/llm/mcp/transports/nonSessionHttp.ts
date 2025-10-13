import cors from 'cors'
import express from 'express'
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js'
import { errorLog } from '@shared/logger'

/*
  Initialize HTTP Transport with both modern and legacy endpoints
*/
const initHttpTransport = (params: { server: McpServer; port: number }) => {
  const { server, port } = params
  const app = express()

  app.use(
    cors({
      origin: '*'
    })
  )
  app.use(express.json())

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

  app.listen(port, (error) => {
    if (error) {
      errorLog(`Failed to start HTTP server: ${error.message}`)
    } else {
      errorLog(`HTTP server listening on http://localhost:${port}`)
      errorLog(
        `Stream chat endpoint available at http://localhost:${port}/stream-chat`
      )
    }
  })
}

export default initHttpTransport
