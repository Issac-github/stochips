import OpenAI from 'openai'
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import registerCallTools from './callLLMToChat'
import registerFilterTools from './callLLMToFilter'

const OPENAI_API_KEY = import.meta.env.MAIN_VITE_OPENAI_API_KEY as string
const OPENAI_BASEURL = import.meta.env.MAIN_VITE_OPENAI_BASEURL as string
const OPENAI_TIMEOUT = parseInt(import.meta.env.MAIN_VITE_OPENAI_TIMEOUT) || 3e4

if (!OPENAI_API_KEY) {
  throw new Error('OPENAI_API_KEY is not set in environment variables.')
}
const openai = new OpenAI({
  apiKey: OPENAI_API_KEY,
  baseURL: OPENAI_BASEURL,
  timeout: OPENAI_TIMEOUT
})

const registerTools = (server: McpServer) => {
  registerCallTools(openai)(server)
  registerFilterTools(openai)(server)
}

export default registerTools
