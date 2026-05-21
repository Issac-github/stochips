import React, { useState } from 'react'
import { Trash2 } from 'lucide-react'
import ChatComposer from '@renderer/components/shared/ChatComposer'
import { type ChatMessage } from '@renderer/components/shared/ChatMessages'
import { Button } from '@renderer/components/ui/button'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle
} from '@renderer/components/ui/card'
import useSocketMcpClient from '@renderer/lib/hooks/useSocketMcpClient'
import { errorLog } from '@shared/logger'
import MCP_KEYS from '@shared/mcpKey'
import McpMessage from './McpMessage'

const McpChat: React.FC = () => {
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
    useSocketMcpClient({ addMessage })

  const sendMessage = async (message: string) => {
    if (!clientRef.current || !message.trim()) return
    setIsLoading(true)
    addMessage({ type: 'user', content: message })
    try {
      const res = await clientRef.current.callTool({
        name: MCP_KEYS.chat_llm,
        arguments: { instruction: message }
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

  return (
    <Card className="flex h-full flex-col overflow-hidden">
      <CardHeader className="flex-row items-center justify-between space-y-0 pb-4">
        <div className="flex items-center gap-3">
          <CardTitle>MCP Chat Interface</CardTitle>
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
        <ChatComposer
          value={inputValue}
          onChange={setInputValue}
          onSubmit={handleSend}
          placeholder="Press Enter to send, Shift+Enter for new line"
          loading={isLoading}
          disabled={!isConnected || isLoading}
        />
      </CardContent>
    </Card>
  )
}

export default McpChat
