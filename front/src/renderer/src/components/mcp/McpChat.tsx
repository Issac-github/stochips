import React, { useEffect, useRef, useState } from 'react'
import { Button, Card, Space, Typography } from 'antd'
import { ClearOutlined } from '@ant-design/icons'
import { Sender } from '@ant-design/x'
import useSocketMcpClient from '@renderer/lib/hooks/useSocketMcpClient'
import { errorLog } from '@shared/logger'
import MCP_KEYS from '@shared/mcpKey'
import McpMessage from './McpMessage'

interface ChatMessage {
  id: string
  type: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  error?: boolean
}

const McpChat: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const addMessage = (message: Omit<ChatMessage, 'id' | 'timestamp'>) => {
    const newMessage: ChatMessage = {
      ...message,
      id: Date.now().toString(),
      timestamp: new Date()
    }
    setMessages((prev) => [...prev, newMessage])
  }

  const { isConnected, connectionError, setConnectionError, clientRef } =
    useSocketMcpClient({
      addMessage
    })

  const sendMessage = async (message: string) => {
    if (!clientRef.current || !message.trim()) {
      return
    }
    setIsLoading(true)
    addMessage({ type: 'user', content: message })
    try {
      const toolName = MCP_KEYS.chat_llm
      const args = { instruction: message }
      const res = await clientRef.current.callTool({
        name: toolName,
        arguments: args
      })

      let responseContent = 'No response from server'
      if (res?.content?.[0]?.text) {
        responseContent = res.content[0].text
      } else if (res?.content?.[0]) {
        responseContent = JSON.stringify(res.content[0], null, 2)
      }
      addMessage({ type: 'assistant', content: responseContent })
    } catch (error) {
      errorLog(error)
      const errorMessage =
        error instanceof Error ? error.message : 'Unknown error occurred'
      addMessage({
        type: 'assistant',
        content: `Error: ${errorMessage}`,
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

  // Removed: Sender component handles Enter/Shift+Enter natively

  const clearChat = () => {
    setMessages([])
  }

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex h-full flex-col overflow-auto">
      <Card
        title={
          <Space>
            <Typography.Title level={4} style={{ margin: 0 }}>
              MCP Chat Interface
            </Typography.Title>
            <Typography.Text type={isConnected ? 'success' : 'secondary'}>
              {isConnected ? '● Connected' : '○ Disconnected'}
            </Typography.Text>
          </Space>
        }
        extra={
          <Button icon={<ClearOutlined />} onClick={clearChat} type="text">
            Clear
          </Button>
        }
        className="flex h-full flex-col"
        classNames={{ body: 'flex-1 flex flex-col p-4 overflow-auto' }}
      >
        {connectionError && (
          <div
            className="mb-4 rounded-lg border border-red-300 bg-red-50 p-3"
            style={{ color: '#d4380d' }}
          >
            <div className="font-semibold">Connection Error</div>
            <div className="text-sm">{connectionError}</div>
            <Button
              size="small"
              type="text"
              style={{ color: '#d4380d' }}
              onClick={() => setConnectionError(null)}
            >
              Close
            </Button>
          </div>
        )}
        <McpMessage messageList={messages} />
        <Sender
          value={inputValue}
          onChange={(val) => setInputValue(val)}
          onSubmit={handleSend}
          placeholder="Press Enter to send, Shift+Enter for new line"
          loading={isLoading}
          disabled={!isConnected || isLoading}
        />
      </Card>
    </div>
  )
}

export default McpChat
