import React, { useState } from 'react'
import { Play, Trash2 } from 'lucide-react'
import ChatComposer from '@renderer/components/shared/ChatComposer'
import { type ChatMessage } from '@renderer/components/shared/ChatMessages'
import { Button } from '@renderer/components/ui/button'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle
} from '@renderer/components/ui/card'
import useHttpMcpClient from '@renderer/lib/hooks/useHttpMcpClient'
import { errorLog } from '@shared/logger'
import MCP_KEYS from '@shared/mcpKey'
import McpMessage from './McpMessage'

const McpFilter: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const addMessage = (message: Omit<ChatMessage, 'id' | 'timestamp'>) => {
    const newMessage: ChatMessage = {
      ...message,
      id: Date.now().toString(),
      timestamp: new Date()
    }
    setMessages((prev) => [...prev, newMessage])
  }

  const { isConnected, connectionError, setConnectionError, clientRef } =
    useHttpMcpClient({ addMessage })

  const sendMessage = async (message: string) => {
    if (!clientRef.current || !message.trim()) return
    setIsLoading(true)
    addMessage({ type: 'user', content: message })
    try {
      const res = await clientRef.current.callTool({
        name: MCP_KEYS.filter_json_llm,
        arguments: {
          data: [
            { id: 1, city: 'Beijing', temperature: 15, aqi: 180 },
            { id: 2, city: 'Shanghai', temperature: 8, aqi: 220 },
            { id: 3, city: 'Guangzhou', temperature: 22, aqi: 150 },
            { id: 4, city: 'Shenzhen', temperature: 25, aqi: 120 },
            { id: 5, city: 'Hangzhou', temperature: 5, aqi: 190 },
            { id: 6, city: 'Nanjing', temperature: 12, aqi: 210 }
          ],
          instruction: message
        }
      })
      const responseContent = res?.content?.[0]?.text
        ? res.content[0].text
        : res?.content?.[0]
          ? JSON.stringify(res.content[0], null, 2)
          : 'No response from server'
      addMessage({ type: 'assistant', content: responseContent })
    } catch (error) {
      errorLog(error)
      addMessage({
        type: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error occurred'}`,
        error: true
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleSend = () => {
    if (inputValue.trim() && !isLoading) {
      sendMessage(inputValue.trim())
      setInputValue('')
    }
  }

  const runSample = async () => {
    await sendMessage(
      '保留空气质量AQI小于200且温度大于等于20的记录，只输出 id 和 city 字段，返回数组。'
    )
  }

  return (
    <Card className="flex h-full flex-col overflow-hidden">
      <CardHeader className="flex-row items-center justify-between space-y-0 pb-4">
        <div className="flex items-center gap-3">
          <CardTitle>JSON Filter (HTTP)</CardTitle>
          <span
            className={
              isConnected
                ? 'rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-600'
                : 'border-border bg-muted text-muted-foreground rounded-full border px-3 py-1 text-xs font-bold'
            }
          >
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
        <Button variant="ghost" size="sm" onClick={() => setMessages([])}>
          <Trash2 className="h-4 w-4" />
          Clear
        </Button>
      </CardHeader>
      <CardContent className="flex min-h-0 flex-1 flex-col p-4">
        {connectionError && (
          <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-red-900">
            <div className="font-semibold">Connection Error</div>
            <div className="text-sm">{connectionError}</div>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setConnectionError(null)}
            >
              Close
            </Button>
          </div>
        )}
        <McpMessage messageList={messages} />
        <div className="flex flex-col gap-2">
          <ChatComposer
            value={inputValue}
            onChange={setInputValue}
            onSubmit={handleSend}
            placeholder="Press Enter to send, Shift+Enter for new line"
            loading={isLoading}
            disabled={!isConnected || isLoading}
          />
          <Button
            onClick={runSample}
            disabled={!isConnected || isLoading}
            variant="outline"
          >
            <Play className="h-4 w-4" />
            Sample
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export default McpFilter
