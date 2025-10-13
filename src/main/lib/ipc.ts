import { initializeDatabase } from '../database/controller/article'
import initLLMServer from '../llm'

const portMap: PortMapType = {
  socket: null,
  http: null,
  gpt: null
}
initializeDatabase()
initLLMServer().then(({ SOCKETPORT, HTTPPORT, GPTPORT }) => {
  // MCP WebSocket server port
  portMap.socket = SOCKETPORT
  // MCP HTTP server port
  portMap.http = HTTPPORT
  // GPT HTTP server port
  portMap.gpt = GPTPORT
})

export { portMap }
