import React, { useEffect, useRef, useState } from 'react'
import { Button, Card, Input, Space, Typography } from 'antd'
import { ClearOutlined, SendOutlined, StopOutlined } from '@ant-design/icons'
import useStreamChat from '@renderer/lib/hooks/useGPTChat'

const { TextArea } = Input
const { Text, Title } = Typography

interface Message {
  id: string
  type: 'user' | 'assistant'
  content: string
  timestamp: Date
  streaming?: boolean
}

const StreamChat: React.FC = () => {
  const currentMessageIdRef = useRef('')
  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  const [messageList, setMessageList] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const { sendStreamMessage, stopStream, isPortReady } = useStreamChat()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messageList])

  const addMessage = (message: Omit<Message, 'id' | 'timestamp'>) => {
    const newMessage: Message = {
      ...message,
      id: `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      timestamp: new Date()
    }
    setMessageList((prev) => [...prev, newMessage])
    return newMessage.id
  }

  const updateMessage = (id: string, content: string) => {
    setMessageList((prev) =>
      prev.map((message) =>
        message.id === id ? { ...message, content } : message
      )
    )
  }

  const finishMessage = (id: string) => {
    setMessageList((prev) =>
      prev.map((message) =>
        message.id === id ? { ...message, streaming: false } : message
      )
    )
  }

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading || !isPortReady) {
      return
    }
    const userMessage = inputValue.trim()
    setInputValue('')
    setIsLoading(true)
    addMessage({ type: 'user', content: userMessage })
    const assistantMessageId = addMessage({
      type: 'assistant',
      content: '',
      streaming: true
    })
    currentMessageIdRef.current = assistantMessageId
    await sendStreamMessage(userMessage, {
      onChunk: (chunk) => {
        setMessageList((prev) =>
          prev.map((message) =>
            message.id === assistantMessageId
              ? { ...message, content: message.content + chunk }
              : message
          )
        )
      },
      onComplete: (_fullText) => {
        finishMessage(assistantMessageId)
        setIsLoading(false)
      },
      onError: (error) => {
        updateMessage(assistantMessageId, `错误: ${error}`)
        finishMessage(assistantMessageId)
        setIsLoading(false)
      }
    })
  }

  const handleStop = () => {
    stopStream()
    if (currentMessageIdRef.current) {
      finishMessage(currentMessageIdRef.current)
    }
    setIsLoading(false)
  }

  const clearChat = () => {
    setMessageList([])
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex h-full flex-col overflow-auto p-1">
      <Card
        title={
          <Space>
            <Title level={4} style={{ margin: 0 }}>
              ChatBot
            </Title>
            <Text type={isPortReady ? 'success' : 'secondary'}>
              {isPortReady ? '● 已连接' : '○ 未连接'}
            </Text>
          </Space>
        }
        extra={
          <Button icon={<ClearOutlined />} onClick={clearChat}>
            清空
          </Button>
        }
        classNames={{ body: 'h-full flex flex-col p-5' }}
        className="flex h-full flex-col"
      >
        <div className="mb-4 h-full flex-1 space-y-4 overflow-auto">
          {messageList.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[70%] rounded-lg p-3 ${
                  message.type === 'user'
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-200 text-gray-800'
                }`}
              >
                <div className="whitespace-pre-wrap">{message.content}</div>
                {message.streaming && (
                  <span className="ml-1 inline-block h-4 w-1 animate-pulse bg-current" />
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <div className="flex items-end gap-2">
          <TextArea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Send message... (Enter to send, Shift+Enter to newline)"
            autoSize={{ minRows: 1, maxRows: 4 }}
            disabled={!isPortReady || isLoading}
            style={{ flex: 1 }}
            size="large"
          />
          {isLoading ? (
            <Button
              danger
              icon={<StopOutlined />}
              onClick={handleStop}
              size="large"
            >
              Stop
            </Button>
          ) : (
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSend}
              disabled={!isPortReady || !inputValue.trim()}
              size="large"
            >
              Send
            </Button>
          )}
        </div>
      </Card>
    </div>
  )
}

export default StreamChat
