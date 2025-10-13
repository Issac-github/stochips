import { useEffect, useRef, useState } from 'react'

interface StreamChatOptions {
  onChunk?: (chunk: string) => void
  onComplete?: (fullText: string) => void
  onError?: (error: string) => void
}

const useGPTChat = () => {
  const [port, setPort] = useState<number | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  useEffect(() => {
    window.api.handleMcpPort.requestMcpPort()
    const unsubscribe = window.api.handleMcpPort.responseMcpPort((portMap) => {
      setPort(portMap.gpt)
    })
    return () => {
      unsubscribe()
    }
  }, [])

  const sendStreamMessage = async (
    instruction: string,
    options: StreamChatOptions = {}
  ) => {
    const { onChunk, onComplete, onError } = options
    if (!port) {
      onError?.('MCP port not available')
      return
    }
    abortControllerRef.current?.abort()
    abortControllerRef.current = new AbortController()
    try {
      const response = await fetch(`http://localhost:${port}/stream-chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ instruction }),
        signal: abortControllerRef.current.signal
      })
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      if (!response.body) {
        throw new Error('Response body is null')
      }
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let fullText = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          break
        }
        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n').filter(Boolean)
        for (const line of lines) {
          if (!line.startsWith('data: ')) {
            continue
          }
          try {
            const data = JSON.parse(line.slice(6))
            if (data.error) {
              onError?.(data.error)
              return
            }
            if (data.done) {
              onComplete?.(fullText)
              return
            }
            if (data.content) {
              fullText += data.content
              onChunk?.(data.content)
            }
          } catch (error) {
            onError?.(
              error instanceof Error ? error.message : 'JSON parse error'
            )
          }
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        return
      }
      options.onError?.(
        error instanceof Error ? error.message : 'Unknown error'
      )
    }
  }

  const stopStream = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
  }

  return {
    sendStreamMessage,
    stopStream,
    isPortReady: port !== null
  }
}

export default useGPTChat
