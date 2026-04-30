import cors from 'cors'
import express from 'express'
import OpenAI from 'openai'
import { debugLog, errorLog } from '@shared/logger'

const OPENAI_MODEL = import.meta.env.MAIN_VITE_OPENAI_MODEL as string
const OPENAI_API_KEY = import.meta.env.MAIN_VITE_OPENAI_API_KEY as string
const OPENAI_BASEURL = import.meta.env.MAIN_VITE_OPENAI_BASEURL as string
const OPENAI_TIMEOUT = parseInt(import.meta.env.MAIN_VITE_OPENAI_TIMEOUT) || 3e4

const initGPTChat = (params: { port: number }) => {
  const { port } = params
  const openai = new OpenAI({
    apiKey: OPENAI_API_KEY,
    baseURL: OPENAI_BASEURL,
    timeout: OPENAI_TIMEOUT
  })
  const app = express()
  app.use(
    cors({
      origin: '*' // Allow all origins
    })
  )
  app.use(express.json())

  debugLog('Setting up /stream-chat endpoint')

  app.post('/stream-chat', async (req, res) => {
    const { instruction } = req.body

    debugLog('Stream chat endpoint hit with instruction:', instruction)

    if (!instruction) {
      res.status(400).json({ error: 'instruction is required' })
      return
    }

    // 设置 SSE 响应头
    res.setHeader('Content-Type', 'text/event-stream')
    res.setHeader('Cache-Control', 'no-cache')
    res.setHeader('Connection', 'keep-alive')

    try {
      const stream = await openai.chat.completions.create(
        {
          model: OPENAI_MODEL,
          messages: [
            { role: 'system', content: 'You are a helpful assistant.' },
            { role: 'user', content: instruction }
          ],
          temperature: 0.7,
          max_tokens: 2048,
          stream: true
        },
        {
          timeout: OPENAI_TIMEOUT
        }
      )

      // 流式发送每个 chunk
      for await (const chunk of stream) {
        const content = chunk.choices[0]?.delta?.content || ''
        if (content) {
          // 发送 SSE 格式的数据
          res.write(`data: ${JSON.stringify({ content })}\n\n`)
        }
      }

      // 发送结束信号
      res.write(`data: ${JSON.stringify({ done: true })}\n\n`)
      res.end()
    } catch (error) {
      errorLog('Stream chat error:', error)
      const errorMessage =
        error instanceof Error ? error.message : 'Unknown error'
      res.write(`data: ${JSON.stringify({ error: errorMessage })}\n\n`)
      res.end()
    }
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

export default initGPTChat
