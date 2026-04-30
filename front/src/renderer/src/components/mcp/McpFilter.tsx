import React, { useEffect, useRef, useState } from 'react'
import { Button, Card, Space, Typography } from 'antd'
import { ClearOutlined } from '@ant-design/icons'
import { Sender } from '@ant-design/x'
import useHttpMcpClient from '@renderer/lib/hooks/useHttpMcpClient'
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

const McpFilter: React.FC = () => {
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
    useHttpMcpClient({
      addMessage
    })
  const sendMessage = async (message: string) => {
    if (!clientRef.current || !message.trim()) {
      return
    }
    setIsLoading(true)
    addMessage({ type: 'user', content: message })
    try {
      const toolName = MCP_KEYS.filter_json_llm
      const args = {
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

  const runSample = async () => {
    const sampleMessage =
      '保留空气质量AQI小于200且温度大于等于20的记录，只输出 id 和 city 字段，返回数组。'
    await sendMessage(sampleMessage)
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
              JSON Filter (HTTP)
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
        <div className="flex flex-col gap-2">
          <Sender
            value={inputValue}
            onChange={(val) => setInputValue(val)}
            onSubmit={handleSend}
            placeholder="Press Enter to send, Shift+Enter for new line"
            loading={isLoading}
            disabled={!isConnected || isLoading}
          />
          <Button
            onClick={runSample}
            disabled={!isConnected || isLoading}
            size="large"
            className="w-full"
          >
            Sample
          </Button>
        </div>
      </Card>
    </div>
  )
}

export default McpFilter
