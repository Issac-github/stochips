import OpenAI from 'openai'
import { z } from 'zod/v3'
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { debugLog, errorLog } from '@shared/logger'
import MCP_KEYS from '@shared/mcpKey'

const OPENAI_MODEL = import.meta.env.MAIN_VITE_OPENAI_MODEL as string
const OPENAI_TIMEOUT = parseInt(import.meta.env.MAIN_VITE_OPENAI_TIMEOUT) || 3e4

const callLLMToChatStream = (openai: OpenAI) => {
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
    const stream = await openai.chat.completions.create(
      {
        model: OPENAI_MODEL,
        messages: [
          { role: 'system', content: system },
          { role: 'user', content: user }
        ],
        temperature: 0.7,
        max_tokens: 2048,
        stream: true
      },
      {
        timeout: OPENAI_TIMEOUT
      }
    )
    return stream
  }
}

const registerCallTools = (openai: OpenAI) => {
  return (server: McpServer) => {
    ;(
      server.registerTool as unknown as (
        name: string,
        config: unknown,
        cb: (
          args: { instruction: string },
          extra: { signal?: AbortSignal }
        ) => Promise<unknown>
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
      async ({ instruction }, { signal }) => {
        debugLog('Chat tool called with:', { instruction })
        try {
          const stream = await callLLMToChatStream(openai)({ instruction })
          let fullResponse = ''
          // 收集流式响应
          for await (const chunk of stream) {
            if (signal?.aborted) {
              throw new Error('Request aborted')
            }
            const content = chunk.choices[0]?.delta?.content || ''
            fullResponse += content
          }
          debugLog('Chat tool result:', fullResponse)
          return {
            content: [
              {
                type: 'text',
                text: fullResponse
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
