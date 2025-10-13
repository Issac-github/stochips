import React, { useEffect, useRef, useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Input,
  Radio,
  Space,
  Spin,
  Typography
} from 'antd'
import { ClearOutlined, SendOutlined } from '@ant-design/icons'
import useHttpMcpClient from '@renderer/lib/hooks/useHttpMcpClient'
import useSocketMcpClient from '@renderer/lib/hooks/useSocketMcpClient'
import { errorLog } from '@shared/logger'
import MCP_KEYS from '@shared/mcpKey'
import McpMessage from './McpMessage'

const { TextArea } = Input
const { Text, Title } = Typography

interface ChatMessage {
  id: string
  type: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  error?: boolean
}

const Mcp: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [chatMode, setChatMode] = useState<'chat' | 'filter'>('chat')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textAreaRef = useRef<HTMLTextAreaElement>(null)

  const addMessage = (message: Omit<ChatMessage, 'id' | 'timestamp'>) => {
    const newMessage: ChatMessage = {
      ...message,
      id: Date.now().toString(),
      timestamp: new Date()
    }
    setMessages((prev) => [...prev, newMessage])
  }

  useHttpMcpClient()
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
      const toolName =
        chatMode === 'chat' ? MCP_KEYS.chat_llm : MCP_KEYS.filter_json_llm
      const args =
        chatMode === 'chat'
          ? { instruction: message }
          : {
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

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

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
    textAreaRef.current?.focus()
  }, [messages])

  return (
    <div className="flex h-full flex-col overflow-auto">
      <Card
        title={
          <Space>
            <Title level={4} style={{ margin: 0 }}>
              MCP Chat Interface
            </Title>
            <Text type={isConnected ? 'success' : 'secondary'}>
              {isConnected ? '● Connected' : '○ Disconnected'}
            </Text>
          </Space>
        }
        extra={
          <Space>
            <Button icon={<ClearOutlined />} onClick={clearChat}>
              Clear
            </Button>
          </Space>
        }
        className="flex h-full flex-col"
        classNames={{ body: 'flex-1 flex flex-col p-4 overflow-auto' }}
      >
        <div className="mb-4 flex items-center justify-between">
          <Radio.Group
            value={chatMode}
            onChange={(e) => setChatMode(e.target.value)}
          >
            {['chat', 'filter'].map((mode) => (
              <Radio.Button key={mode} value={mode}>
                {mode === 'chat' ? 'Chat' : 'Filter'}
              </Radio.Button>
            ))}
          </Radio.Group>
          {connectionError && (
            <Alert
              className="mb-4"
              message="Connection Error"
              description={connectionError}
              type="error"
              closable
              onClose={() => setConnectionError(null)}
            />
          )}
        </div>
        <McpMessage messageList={messages} />
        <div className="flex items-end gap-4">
          <TextArea
            ref={textAreaRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Press Enter to send, Shift+Enter for new line"
            autoSize={{ minRows: 1, maxRows: 4 }}
            disabled={!isConnected || isLoading}
            style={{ flex: 1 }}
            size="large"
            autoFocus={true}
          />
          {chatMode === 'filter' && (
            <Button
              onClick={runSample}
              disabled={!isConnected || isLoading}
              size="large"
              type="primary"
            >
              Run Sample
            </Button>
          )}
          <Button
            type="primary"
            icon={isLoading ? <Spin size="small" /> : <SendOutlined />}
            onClick={handleSend}
            disabled={!isConnected || isLoading || !inputValue.trim()}
            size="large"
          >
            {isLoading ? 'Sending...' : 'Send'}
          </Button>
        </div>
      </Card>
    </div>
  )
}

export default Mcp
