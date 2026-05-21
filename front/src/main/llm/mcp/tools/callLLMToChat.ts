import OpenAI from 'openai'
import { z } from 'zod/v3'
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { debugLog, errorLog } from '@shared/logger'
import MCP_KEYS from '@shared/mcpKey'

const OPENAI_MODEL = import.meta.env.MAIN_VITE_OPENAI_MODEL as string
const OPENAI_TIMEOUT = parseInt(import.meta.env.MAIN_VITE_OPENAI_TIMEOUT) || 3e4

const callLLMToChat = (openai: OpenAI) => {
  return async ({ instruction }) => {
    const system = `You are a helpful assistant.`
    const user = instruction
    debugLog(
      'Calling LLM with instruction:',
      instruction,
      '\n',
      'Sending to OpenAI:',
      { system, user }
    )
    const completion = await openai.chat.completions.create(
      {
        model: OPENAI_MODEL,
        messages: [
          { role: 'system', content: system },
          { role: 'user', content: user }
        ],
        temperature: 0.7,
        max_tokens: 2048
      },
      {
        timeout: OPENAI_TIMEOUT
      }
    )
    return completion?.choices
      ?.map((choice) => choice.message?.content || '')
      ?.join('\n')
  }
}

const registerCallTools = (openai: OpenAI) => {
  return (server: McpServer) => {
    ;(
      server.registerTool as unknown as (
        name: string,
        config: unknown,
        cb: (args: { instruction: string }) => Promise<unknown>
      ) => void
    )(
      MCP_KEYS.chat_llm,
      {
        title: 'General Chat',
        description: 'A general-purpose chat function using an LLM',
        inputSchema: {
          instruction: z.string().min(1)
        }
      },
      async ({ instruction }) => {
        debugLog('Chat tool called with:', { instruction })
        try {
          const output = await callLLMToChat(openai)({ instruction })
          debugLog('Chat tool result:', output)
          return {
            content: [
              {
                type: 'text',
                text:
                  typeof output === 'string' ? output : JSON.stringify(output)
              }
            ]
          }
        } catch (error) {
          errorLog('Chat tool error:', error)
          throw error
        }
      }
    )
  }
}

export default registerCallTools
