import OpenAI from 'openai'
import { z } from 'zod'
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { debugLog, errorLog } from '@shared/logger'
import MCP_KEYS from '@shared/mcpKey'

const OPENAI_MODEL = import.meta.env.MAIN_VITE_OPENAI_MODEL as string
const OPENAI_TIMEOUT = parseInt(import.meta.env.MAIN_VITE_OPENAI_TIMEOUT) || 3e4

const FilterInputSchema = z.object({
  data: z.any(),
  instruction: z.string().min(1)
})

const FilterOutputSchema = z.object({
  result: z.any(),
  meta: z
    .object({
      model: z.string(),
      tokens_estimate: z.number().int().nonnegative().optional()
    })
    .optional()
})

const callLLMToFilter = (openai: OpenAI) => {
  return async ({ data, instruction }) => {
    const system = `You are a precise JSON filter. Follow the instruction to filter the provided JSON.\n- Always answer with valid minified JSON.\n- No extra keys, text, or code fences.\n- If nothing matches, return an empty array [] when input is array, or {} when input is object.\n- Preserve input fields unless removal is required to satisfy the instruction.\n`
    const user = [
      'Instruction:',
      instruction,
      'Input JSON:',
      JSON.stringify(data),
      'Return ONLY the resulting JSON (no prose, no markdown).'
    ].join('\n')

    debugLog(
      'Sending to OpenAI:',
      { system, user },
      '\n',
      'Calling LLM with data:',
      data,
      'instruction:',
      instruction
    )
    const completion = await openai.chat.completions.create(
      {
        model: OPENAI_MODEL,
        messages: [
          { role: 'system', content: system },
          { role: 'user', content: user }
        ],
        temperature: 0,
        max_tokens: 2048
      },
      {
        timeout: OPENAI_TIMEOUT
      }
    )

    const contents = completion.choices
      ?.map((c) => c.message?.content?.trim() || '')
      .filter(Boolean)
    const parsed: unknown[] = []
    for (const jsonStr of contents) {
      try {
        parsed.push(JSON.parse(jsonStr))
      } catch (error) {
        errorLog('Failed to parse JSON:', error, 'Content:', jsonStr)
        const start = Math.min(
          ...['{', '['].map((sym) => jsonStr.indexOf(sym)).filter((i) => i >= 0)
        )
        const end = Math.max(
          ...['}', ']'].map((sym) => jsonStr.lastIndexOf(sym))
        )
        if (start >= 0 && end > start) {
          const candidate = jsonStr.slice(start, end + 1)
          try {
            parsed.push(JSON.parse(candidate))
          } catch (e) {
            errorLog(
              'Still failed to parse candidate JSON:',
              e,
              'Candidate:',
              candidate
            )
            throw new Error('Model did not return valid JSON.')
          }
        } else {
          throw new Error('Model did not return valid JSON.')
        }
      }
    }
    return FilterOutputSchema.parse({
      result: parsed,
      meta: { model: OPENAI_MODEL }
    })
  }
}

const registerFilterTools = (openai: OpenAI) => {
  return (server: McpServer) => {
    server.registerTool(
      MCP_KEYS.filter_json_llm,
      {
        title: 'JSON Filter',
        description:
          'Filter input JSON using a natural language instruction via LLM',
        inputSchema: FilterInputSchema.shape
      },
      async ({ data, instruction }) => {
        debugLog('Tool called with:', { data, instruction })
        try {
          const output = await callLLMToFilter(openai)({ data, instruction })
          debugLog('Tool result:', output)
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(output.result)
              }
            ]
          }
        } catch (error) {
          errorLog('Tool error:', error)
          throw error
        }
      }
    )
  }
}

export default registerFilterTools
