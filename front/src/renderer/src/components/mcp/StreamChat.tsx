import React, { useEffect, useRef, useState } from 'react'
import { Button, Card, Space, Typography } from 'antd'
import { ClearOutlined, SendOutlined, StopOutlined } from '@ant-design/icons'
import { Bubble, Sender } from '@ant-design/x'
import { XMarkdown } from '@ant-design/x-markdown'
import { ANTD_MAP_TOKEN } from '@renderer/assets/style/color'
import useStreamChat from '@renderer/lib/hooks/useGPTChat'

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

  return (
    <div className="flex h-full flex-col overflow-auto">
      <Card
        title={
          <Space>
            <Typography.Title level={4} style={{ margin: 0 }}>
              Streaming Chat (HTTP)
            </Typography.Title>
            <Typography.Text type={isPortReady ? 'success' : 'secondary'}>
              {isPortReady ? '● Connected' : '○ Disconnected'}
            </Typography.Text>
          </Space>
        }
        extra={
          <Button icon={<ClearOutlined />} onClick={clearChat} type="text">
            Clear
          </Button>
        }
        classNames={{ body: 'h-full flex flex-col p-4 overflow-auto' }}
        className="flex h-full flex-col"
      >
        <div
          className="mb-4 h-full flex-1 overflow-auto rounded-lg p-4"
          style={{ border: `1px solid ${ANTD_MAP_TOKEN.colorBorderSecondary}` }}
        >
          {!messageList.length ? (
            <div
              className="flex h-full flex-col items-center justify-center text-center"
              style={{ color: ANTD_MAP_TOKEN.colorTextSecondary }}
            >
              <SendOutlined
                style={{ fontSize: '48px', marginBottom: '16px' }}
              />
              <div>Start chatting with the AI</div>
            </div>
          ) : (
            messageList.map((message) => (
              <div key={message.id} style={{ marginBottom: '16px' }}>
                <Bubble
                  placement={message.type === 'user' ? 'end' : 'start'}
                  content={<XMarkdown>{message.content || ''}</XMarkdown>}
                />
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        <Sender
          value={inputValue}
          onChange={(val) => setInputValue(val)}
          onSubmit={handleSend}
          placeholder="Send message... (Enter to send, Shift+Enter to newline)"
          loading={isLoading}
          disabled={!isPortReady || isLoading}
          prefix={isLoading ? <StopOutlined onClick={handleStop} /> : undefined}
        />
      </Card>
    </div>
  )
}

export default StreamChat
